#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
文档解析集成模块
将文档解析功能集成到原有的Streamlit页面中
"""

import streamlit as st
import os
from pathlib import Path
from document_parser import DocumentProcessor
import tempfile
import shutil


class DocumentIntegration:
    """文档解析集成类"""
    
    def __init__(self):
        """初始化集成模块"""
        self.processor = None
        self.temp_dir = None
    
    def init_processor(self, config_path: str = "config.ini"):
        """初始化文档处理器"""
        try:
            self.processor = DocumentProcessor(config_path)
            return True
        except Exception as e:
            st.error(f"初始化文档处理器失败: {e}")
            return False
    
    def create_temp_directory(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp(prefix="streamlit_doc_")
        return self.temp_dir
    
    def cleanup_temp_directory(self):
        """清理临时目录"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                st.warning(f"清理临时目录失败: {e}")
    
    def process_uploaded_document(self, uploaded_file) -> str:
        """
        处理上传的文档
        
        Args:
            uploaded_file: Streamlit上传的文件对象
            
        Returns:
            处理后的文档文本
        """
        if not self.processor:
            st.error("文档处理器未初始化")
            return ""
        
        try:
            # 创建临时目录
            temp_dir = self.create_temp_directory()
            
            # 保存上传的文件到临时目录
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            # 处理文档
            with st.spinner("正在解析文档中的图片..."):
                processed_content = self.processor.process_document(temp_file_path)
            
            return processed_content
            
        except Exception as e:
            st.error(f"文档处理失败: {e}")
            return ""
        
        finally:
            # 清理临时目录
            self.cleanup_temp_directory()
    
    def render_document_upload_section(self):
        """渲染文档上传区域"""
        st.subheader("📄 文档解析功能")
        
        # 文档上传
        uploaded_doc = st.file_uploader(
            "上传带图片的文档",
            type=["docx", "pdf", "txt"],
            help="支持Word文档(.docx)、PDF文件(.pdf)和文本文件(.txt)"
        )
        
        if uploaded_doc is not None:
            # 显示文件信息
            file_details = {
                "文件名": uploaded_doc.name,
                "文件类型": uploaded_doc.type,
                "文件大小": f"{uploaded_doc.size / 1024:.2f} KB"
            }
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.write("**文件信息:**")
                for key, value in file_details.items():
                    st.write(f"{key}: {value}")
            
            with col2:
                # 处理按钮
                if st.button("🔍 解析文档", type="primary"):
                    if self.init_processor():
                        # 处理文档
                        processed_text = self.process_uploaded_document(uploaded_doc)
                        
                        if processed_text:
                            st.success("✅ 文档解析完成！")
                            
                            # 显示处理结果
                            with st.expander("📋 解析结果", expanded=True):
                                st.text_area(
                                    "处理后的文档内容",
                                    value=processed_text,
                                    height=300,
                                    help="图片已被转换为文字描述或流程图文本"
                                )
                            
                            # 下载处理后的文档
                            st.download_button(
                                label="📥 下载处理后的文档",
                                data=processed_text,
                                file_name=f"processed_{uploaded_doc.name}.txt",
                                mime="text/plain",
                                help="下载处理后的文档，图片已转换为文字描述"
                            )
                        else:
                            st.error("❌ 文档解析失败")
                    else:
                        st.error("❌ 文档处理器初始化失败")
        
        # 功能说明
        with st.expander("ℹ️ 功能说明"):
            st.markdown("""
            ### 文档解析功能说明
            
            **支持的文件格式：**
            - 📄 Word文档 (.docx)
            - 📄 PDF文件 (.pdf)  
            - 📄 文本文件 (.txt)
            
            **处理能力：**
            - 🔍 **图片识别**：自动识别文档中的图片内容
            - 🖥️ **UI界面描述**：将UI截图转换为详细的界面描述
            - 🔄 **流程图转换**：将流程图转换为Mermaid语法文本
            - 📝 **文字描述**：将其他类型图片转换为文字描述
            
            **处理流程：**
            1. 上传文档文件
            2. 系统自动提取文档中的图片
            3. AI模型识别图片内容
            4. 根据图片类型生成相应的文字描述
            5. 将图片占位符替换为识别结果
            6. 输出处理后的完整文档
            
            **注意事项：**
            - 图片识别需要配置有效的AI模型API
            - 处理时间取决于文档大小和图片数量
            - 建议图片清晰度较高以获得更好的识别效果
            """)
    
    def cleanup(self):
        """清理资源"""
        if self.processor:
            self.processor.cleanup()
        self.cleanup_temp_directory()


# 在原有页面中集成的示例函数
def integrate_document_parser_to_page():
    """
    将文档解析功能集成到原有页面的示例函数
    可以在page.py中调用此函数来添加文档解析功能
    """
    
    # 创建集成实例
    doc_integration = DocumentIntegration()
    
    # 在页面中添加文档解析标签页
    doc_tab1, doc_tab2 = st.tabs(["📄 文档解析", "🤖 AI交互"])
    
    with doc_tab1:
        # 渲染文档上传区域
        doc_integration.render_document_upload_section()
    
    with doc_tab2:
        # 原有的AI交互功能
        st.info("请在原有页面中实现AI交互功能")
    
    # 页面结束时清理资源
    st.session_state['doc_integration'] = doc_integration


# 清理函数，用于页面结束时清理资源
def cleanup_document_integration():
    """清理文档集成资源"""
    if 'doc_integration' in st.session_state:
        st.session_state['doc_integration'].cleanup()
        del st.session_state['doc_integration']


if __name__ == "__main__":
    # 测试集成功能
    st.set_page_config(
        page_title="文档解析测试",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 文档解析功能测试")
    
    # 运行集成功能
    integrate_document_parser_to_page() 