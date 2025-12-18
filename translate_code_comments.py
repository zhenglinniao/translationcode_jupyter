
import json
import logging
import re
import os
import argparse
import configparser
import openai

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 读取配置 (复用 ai_translate 的配置逻辑)
def setup_openai():
    config = configparser.ConfigParser()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    config.read(config_path)
    
    api_key = config.get('OpenAI', 'api_key')
    base_url = config.get('OpenAI', 'base_url')
    model_name = config.get('OpenAI', 'model_name')
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    return client, model_name

CLIENT, MODEL_NAME = setup_openai()

CODE_COMMENT_PROMPT = """
You are a professional Python code translator. Your task is to translate code comments from English to Chinese.

CRITICAL RULES:
1. **NO CODE TRANSLATION**: Do NOT translate any Python keywords (def, class, import), variable names (e.g., student_id, df_results), or function names.
2. **NO LINKS/IMAGES**: Do NOT translate URLs (http://...), file paths, or image references.
3. **PRESERVE FORMAT**: Keep the original Markdown formatting inside docstrings intact.
4. **ONLY COMMENTS**: Translate only the explanatory human language text.

Example:
Input: "# Calculate the standard deviation of valid_scores."
Output: "# 计算 valid_scores 的标准差。"

Input: "# See: https://example.com/api"
Output: "# 参见: https://example.com/api"

Input: 'param x: The input tensor.'
Output: 'param x: 输入张量。'

Translate the following comment securely:
"""

def translate_comment_specific(text):
    """
    使用专门的 prompt 翻译注释，保护变量和链接
    """
    # 简单的预处理，如果文本太短或者是纯代码符号，直接返回
    if len(text.strip()) < 2 or not any(c.isalpha() for c in text):
        return text

    try:
        response = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": CODE_COMMENT_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.1 # 低温度以保持准确性
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Translation API error: {e}")
        return text

def extract_and_replace_comments(source_code):
    """
    解析代码，提取注释，翻译并替换
    """
    # 也就是我们主要的逻辑。
    # 为了简化且避免复杂的 token 匹配，我们使用分步替换策略：
    # 1. 找到所有 docstring 位置
    # 2. 找到所有 # 注释位置 (排除 docstring 内部的 #)
    # 3. 按位置倒序替换
    
    replacements = [] # list of (start, end, translated_content)

    # 1. Docstrings
    docstring_pattern = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')')
    for match in docstring_pattern.finditer(source_code):
        original = match.group()
        # 去掉引号翻译内容
        quote_len = 3
        content = original[quote_len:-quote_len]
        
        if content.strip():
            logging.info(f"    Processing docstring: {content.strip()[:20]}...")
            trans = translate_comment_specific(content)
            # 重新组装
            quote = original[:3]
            new_doc = f"{quote}{trans}{quote}"
            replacements.append((match.start(), match.end(), new_doc))
    
    # 2. Single line comments (#)
    # 简单按行处理，如果在 docstring 范围内则忽略
    lines = source_code.split('\n')
    current_pos = 0
    
    # 构建 docstring 范围列表以便快速查找
    doc_ranges = [(r[0], r[1]) for r in replacements]
    
    for line in lines:
        comment_idx = line.find('#')
        if comment_idx != -1:
            abs_start = current_pos + comment_idx
            
            # 检查是否在 docstring 内部
            in_docstring = False
            for start, end in doc_ranges:
                if start <= abs_start < end:
                    in_docstring = True
                    break
            
            if not in_docstring:
                comment_content = line[comment_idx+1:] # 内容不含 #
                # 检查 # 前面是不是有引号未闭合（简单的字符串检测）
                # 这是一个简化的检测，无法处理非常复杂的嵌套引号
                pre_code = line[:comment_idx]
                if pre_code.count('"') % 2 == 0 and pre_code.count("'") % 2 == 0:
                    if comment_content.strip():
                        logging.info(f"    Processing comment: {comment_content.strip()[:20]}...")
                        trans = translate_comment_specific(comment_content)
                        new_line_comment = f"#{trans}" # 这里我们不加空格，因为 trans 可能会自带或者由 prompt 控制，这里简单加个#
                        # 实际上最好是保留原来的空格。
                        # 改进：只替换内容
                        replacements.append((abs_start, current_pos + len(line), new_line_comment))
        
        current_pos += len(line) + 1 # +1 for \n

    # 3. Execute replacements in reverse order
    replacements.sort(key=lambda x: x[0], reverse=True)
    
    new_source = source_code
    for start, end, text in replacements:
        new_source = new_source[:start] + text + new_source[end:]
        
    return new_source

def translate_code_comments(input_file):
    output_file = os.path.splitext(input_file)[0] + '_comment_translated.ipynb'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    total_cells = len(notebook['cells'])
    
    for index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] == 'code':
            logging.info(f"Processing Cell {index + 1}/{total_cells}")
            source_lines = cell['source']
            source_code = ''.join(source_lines)
            
            try:
                new_code = extract_and_replace_comments(source_code)
                # Convert back to list of lines keeping ends
                cell['source'] = new_code.splitlines(keepends=True)
            except Exception as e:
                logging.error(f"Error processing cell {index}: {e}")
                
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Translation complete. Saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Translate comments in Jupyter Notebook code cells.')
    parser.add_argument('input_file', type=str, help='Input .ipynb file')
    args = parser.parse_args()
    
    translate_code_comments(args.input_file)
