# Jupyter Notebook 翻译工具

这是一个用于将 Jupyter Notebook 中的 Markdown 单元格翻译为中文的工具。

## 功能

- 将 .ipynb 文件中的 Markdown 单元格翻译为中文
- 提供两种翻译引擎：阿里云机器翻译和 AI 翻译
- 保留原文，在原文后添加翻译后的文本
- 对原文进行分段，对于每一段单独进行翻译和拼接，方便阅读
- 自动处理和保留特殊的 Markdown 语法元素
- 在使用 AI 翻译时，如果产生了生成过长无关内容的幻觉现象，则自动进行检测并重新翻译

## 安装

1. 克隆此仓库:

```bash
git clone https://github.com/zhenglinniao/translationcode_jupyter.git
cd jupyter-translate
```

2. 安装依赖:

```bash
pip install -r requirements.txt
```

3. 配置:
   

在 `config.ini`，配置阿里云机器翻译的密钥、兼容 OpenAI 接口协议的大模型 API 密钥、请求地址、模型名称。

## 使用方法

使用以下命令运行翻译工具:





```bash
python translate_code_comments.py notebook.ipynb
```

这将生成一个名为 `notebook_zh_comment_translated.ipynb` 的新文件。


