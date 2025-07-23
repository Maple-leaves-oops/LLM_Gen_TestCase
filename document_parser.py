#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
文档解析模块 - 处理带图片的文档
功能：
1. 从文档中提取图片
2. 使用AI识别图片内容
3. 将图片转换为文字描述或流程图文本
4. 替换原文档中的图片占位符
"""

import os
import re
import base64
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from io import BytesIO
import asyncio
import json

# 文档处理相关
import docx
# from docx.document import Document
from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from docx.oxml import parse_xml
from docx.oxml.ns import qn

# 图片处理相关
from PIL import Image
import fitz  # PyMuPDF
import cv2
import numpy as np

# AI模型相关
from autogen_ext.models.openai import OpenAIChatCompletionClient
from configparser import ConfigParser
from llms import *
import openai

class DocumentParser:
    """文档解析器 - 处理带图片的文档"""
    
    def __init__(self, config_path: str = "config.ini"):
        """
        初始化文档解析器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.conf = ConfigParser()
        self.conf.read(config_path, encoding='utf-8')
        
        # 图片占位符格式
        self.image_placeholder_format = "{{IMAGE_PLACEHOLDER_{}}}"
        
        # 临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="doc_parser_")
        
        # 初始化AI客户端
        self._init_ai_clients()
    
    def _init_ai_clients(self):
        """初始化AI客户端（不再使用OpenAIChatCompletionClient，仅保留配置）"""
        try:
            self.doubao_model = self.conf['doubao']['model']
            self.doubao_base_url = self.conf['doubao']['base_url']
            self.doubao_api_key = self.conf['doubao']['api_key']
        except Exception as e:
            print(f"读取doubao模型配置失败: {e}")
            self.doubao_model = None
            self.doubao_base_url = None
            self.doubao_api_key = None

    def parse_document(self, file_path: str) -> str:
        """
        解析文档，提取图片并转换为文字描述
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            处理后的文档文本
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.docx':
            return self._parse_docx(file_path)
        elif file_ext == '.pdf':
            return self._parse_pdf(file_path)
        elif file_ext == '.txt':
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
    
    def _parse_docx(self, file_path: str) -> str:
        """解析Word文档"""
        doc = Document(file_path)
        extracted_text = []
        image_counter = 0
        
        for element in doc.element.body:
            if isinstance(element, CT_P):
                # 处理段落
                paragraph = Paragraph(element, doc)
                text = paragraph.text.strip()
                
                # 检查段落中是否包含图片
                images = self._extract_images_from_paragraph(paragraph)
                if images:
                    for img in images:
                        # 保存图片
                        img_path = self._save_image(img, f"image_{image_counter}")
                        image_counter += 1
                        
                        # 添加图片占位符
                        extracted_text.append(self.image_placeholder_format.format(image_counter - 1))
                else:
                    if text:
                        extracted_text.append(text)
            
            elif isinstance(element, CT_Tbl):
                # 处理表格
                table = Table(element, doc)
                table_text = self._extract_table_text(table)
                if table_text:
                    extracted_text.append(table_text)
        
        # 处理图片识别
        processed_text = self._process_images(extracted_text)
        
        return '\n'.join(processed_text)
    
    def _parse_pdf(self, file_path: str) -> str:
        """解析PDF文档"""
        doc = fitz.open(file_path)
        extracted_text = []
        image_counter = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # 提取文本
            text = page.get_text()
            if text.strip():
                extracted_text.append(text.strip())
            
            # 提取图片
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # 保存图片
                img_path = self._save_image_bytes(image_bytes, f"image_{image_counter}")
                image_counter += 1
                
                # 添加图片占位符
                extracted_text.append(self.image_placeholder_format.format(image_counter - 1))
        
        doc.close()
        
        # 处理图片识别
        processed_text = self._process_images(extracted_text)
        
        return '\n'.join(processed_text)
    
    def _parse_txt(self, file_path: str) -> str:
        """解析纯文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_images_from_paragraph(self, paragraph: Paragraph) -> List[bytes]:
        """从段落中提取图片"""
        images = []
        
        for run in paragraph.runs:
            for element in run.element:
                if element.tag.endswith('drawing'):
                    # 提取图片数据
                    blip = element.find('.//a:blip', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
                    if blip is not None:
                        embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                        if embed:
                            # 获取图片数据
                            image_part = paragraph.part.related_parts[embed]
                            images.append(image_part.blob)
        
        return images
    
    def _extract_table_text(self, table: Table) -> str:
        """提取表格文本"""
        table_text = []
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    row_text.append(cell_text)
            if row_text:
                table_text.append(' | '.join(row_text))
        
        return '\n'.join(table_text) if table_text else ""
    
    def _save_image(self, image_data: bytes, filename: str) -> str:
        """保存图片到临时目录"""
        img_path = os.path.join(self.temp_dir, f"{filename}.png")
        with open(img_path, 'wb') as f:
            f.write(image_data)
        return img_path
    
    def _save_image_bytes(self, image_bytes: bytes, filename: str) -> str:
        """保存图片字节数据到临时目录"""
        img_path = os.path.join(self.temp_dir, f"{filename}.png")
        with open(img_path, 'wb') as f:
            f.write(image_bytes)
        return img_path
    
    def _process_images(self, text_parts: List[str]) -> List[str]:
        """处理图片识别和替换（判断配置是否齐全）"""
        if not (self.doubao_model and self.doubao_base_url and self.doubao_api_key):
            return text_parts
        
        processed_parts = []
        
        for part in text_parts:
            # 检查是否是图片占位符
            placeholder_match = re.search(r'\{IMAGE_PLACEHOLDER_(\d+)\}', part)
            if placeholder_match:
                image_index = int(placeholder_match.group(1))
                img_path = os.path.join(self.temp_dir, f"image_{image_index}.png")
                
                if os.path.exists(img_path):
                    # 识别图片内容
                    image_description = self._recognize_image(img_path)
                    processed_parts.append(image_description)
                else:
                    processed_parts.append(part)
            else:
                processed_parts.append(part)
        
        return processed_parts
    
    def _recognize_image(self, image_path: str) -> str:
        """使用openai官方接口识别图片内容（使用doubao配置）"""
        try:
            # 将图片转换为base64
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # 构建识别提示
            system_message = """你是一个专业的图片内容识别专家。请分析图片内容并按照以下规则输出：

            1. 如果是UI界面图：
            - 详细描述界面布局、组件、功能区域
            - 说明各个按钮、输入框、菜单等元素的位置和作用
            - 描述整体设计风格和用户体验

            2. 如果是流程图：
            - 转换为Mermaid流程图语法
            - 保持原有的逻辑关系和流程顺序
            - 使用标准的Mermaid语法格式

            3. 如果是其他类型的图：
            - 提供详细的文字描述
            - 说明图片的主要内容和关键信息

            请直接输出识别结果，不要添加额外的解释。"""

            user_message = f"""请识别以下图片内容：

            ![图片](data:image/png;base64,{img_base64})

            请根据图片类型进行相应的处理。"""
            
            prompt_messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]

            # 设置openai参数
            openai.api_key = self.doubao_api_key
            openai.base_url = self.doubao_base_url
            
            # 兼容openai-python 1.x/0.x
            try:
                response = openai.chat.completions.create(
                    model=self.doubao_model,
                    messages=prompt_messages,
                    max_tokens=16384,
                    timeout=60
                )
                content = response.choices[0].message.content.strip()
            except AttributeError:
                # 兼容旧版openai
                response = openai.ChatCompletion.create(
                    model=self.doubao_model,
                    messages=prompt_messages,
                    max_tokens=20480,
                    timeout=60
                )
                content = response["choices"][0]["message"]["content"].strip()
            
            if content:
                return content
            else:
                return f"[图片识别失败: {os.path.basename(image_path)}]"
        except Exception as e:
            print(f"图片识别失败: {e}")
            return f"[图片识别错误: {os.path.basename(image_path)}]"
    
    def cleanup(self):
        """清理临时文件"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理临时文件失败: {e}")


class DocumentProcessor:
    """文档处理器 - 提供高级接口"""
    
    def __init__(self, config_path: str = "config.ini"):
        """
        初始化文档处理器
        
        Args:
            config_path: 配置文件路径
        """
        self.parser = DocumentParser(config_path)
    
    def process_document(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        处理文档并返回结果
        
        Args:
            file_path: 输入文档路径
            output_path: 输出文件路径（可选）
            
        Returns:
            处理后的文档内容
        """
        try:
            # 解析文档
            processed_content = self.parser.parse_document(file_path)
            
            # 保存到文件（如果指定了输出路径）
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
            
            return processed_content
            
        except Exception as e:
            print(f"文档处理失败: {e}")
            raise
    
    def process_document_async(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        异步处理文档
        
        Args:
            file_path: 输入文档路径
            output_path: 输出文件路径（可选）
            
        Returns:
            处理后的文档内容
        """
        return asyncio.run(self._async_process(file_path, output_path))
    
    async def _async_process(self, file_path: str, output_path: Optional[str] = None) -> str:
        """异步处理实现"""
        # 这里可以实现异步处理逻辑
        return self.process_document(file_path, output_path)
    
    def cleanup(self):
        """清理资源"""
        self.parser.cleanup()


# 使用示例
if __name__ == "__main__":
    # 创建处理器
    processor = DocumentProcessor()
    
    try:
        # 处理文档
        input_file = "/Users/ninebot/Desktop/移动OA系统可规划为一个四层的安全控制域.docx"  # 替换为实际文件路径
        output_file = "processed_需求文档示例.txt"

        if os.path.exists(input_file):
            result = processor.process_document(input_file, output_file)
            print("文档处理完成！")
            print("处理结果预览:")
            print(result[:500] + "..." if len(result) > 500 else result)
        else:
            print(f"文件不存在: {input_file}")
    
    except Exception as e:
        print(f"处理失败: {e}")
    
    finally:
        # 清理资源
        processor.cleanup()