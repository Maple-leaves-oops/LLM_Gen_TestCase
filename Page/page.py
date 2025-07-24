import streamlit as st
import os
import pandas as pd


class Page:
    def __init__(self):
        self.base_init()
        self.css_init()
        self.html__init()

    @staticmethod
    def base_init():
        st.set_page_config(
            page_title="LLM生成测试用例",
            page_icon=":rocket:",
            layout="wide"
        )

    @staticmethod
    def css_init():
        pass

    @staticmethod
    def html__init():
        with st.sidebar:
            expander1 = st.expander("**使用说明**", True)
            with expander1:
                st.markdown(
                    """
                    ### **使用步骤**
        
                    ### **选项设置**
                    """
                    , unsafe_allow_html=True)
            expander2 = st.expander("**模型说明**", True)
            with expander2:
                st.markdown(
                    """
                    ### **生成用例**
                    
                    ### **评审用例**
                    """
                )

        # 定义一个函数来处理模型参数设置
        # TODO 参数需要根据yaml（暂定）配置文件来设置，包括index参数
        # 当多个控件具有相同的标签或默认值时，它们会被认为是重复的，所以为每个st控件添加一个唯一的key_prefix参数，避免冲突。
        def model_param_section(title, col_widths=None, need_to_config_value="need_to_config", key_prefix=""):
            if col_widths is None:
                col_widths = [1, 1, 1]
            st.subheader(title)
            cols = st.columns(col_widths)

            api_key = cols[0].text_input(f"{need_to_config_value}_api_key", value=need_to_config_value,
                                         help="输入模型的api_key", key=f"{key_prefix}_api_key")
            base_url = cols[1].selectbox("base_url", [need_to_config_value], index=0, help="输入模型的api接口地址",
                                         key=f"{key_prefix}_base_url")
            model = cols[2].selectbox("model", [need_to_config_value], index=0, help="选择模型来完成该部分任务",
                                      key=f"{key_prefix}_model")
            max_tokens = cols[0].number_input(f"{model}最大输出Token:",
                                              max_value=2048,
                                              min_value=0,
                                              value=0,
                                              help=f"最大值：2048；最小值：0", key=f"{key_prefix}_max_tokens")
            temperature = cols[1].number_input(f"{model}模型随机性参数temperature:",
                                               max_value=20,
                                               min_value=0,
                                               value=0,
                                               help="模型随机性参数，数字越大，生成的结果随机性越大，一般为0.7，如果希望AI提供更多的想法，可以调大该数字",
                                               key=f"{key_prefix}_temperature")
            top_p = cols[2].number_input(f"{model}模型随机性参数top:",
                                         max_value=10,
                                         min_value=0,
                                         value=0,
                                         help="模型随机性参数，接近 1 时：模型几乎会考虑所有可能的词，只有概率极低的词才会被排除，随机性也越强；",
                                         key=f"{key_prefix}_top_p")

            return api_key, base_url, model, max_tokens, temperature, top_p

        pagination_1, pagination_2 = st.tabs(["模型设置", "功能交互"])

        with pagination_1:
            api_key_1, base_url_1, model_1, max_tokens_1, temperature_1, top_p_1 = model_param_section(
                "编写用例模型参数设置（更多参数等待探索）", key_prefix="param_1"
            )

            api_key_2, base_url_2, model_2, max_tokens_2, temperature_2, top_p_2 = model_param_section(
                "评审用例模型参数设置", key_prefix="param_2"
            )

            api_key_3, base_url_3, model_3, max_tokens_3, temperature_3, top_p_3 = model_param_section(
                "文档解析模型参数设置", key_prefix="param_3"
            )
            # TODO 保存的配置信息需要传给模型
            if st.button("保存配置"):
                pass

        with pagination_2:
            cols = st.columns([1, 1])

            # 测试用例参数配置
            with cols[0].expander(":rose: **测试用例参数配置（可选）**"):
                # 添加测试用例数量控制
                test_case_count_range = st.slider("生成测试用例数量范围", help="指定生成的测试用例数"
                                                                               "量范围", min_value=0,
                                                  max_value=100, value=(5, 10), step=1)
            # 支持上传人工测试用例用于对比
            # upload_manual_test_cases = cols[0].checkbox(":heart: **上传人工测试用例（需要支持更多常见格式）**", False)
            # st.session_state是Streamlit提供的一个机制，用于存储和共享应用中的状态（如变量值），
            # 从而在不同的交互和页面刷新之间保持数据的持续性，一些状态值（动态变化）都推荐使用st.session_state来控制
            # if 'upload_manual_test_cases' not in st.session_state:
            #     st.session_state.upload_manual_test_cases = False
            # if cols[0].button(":heart: **上传人工测试用例（可选）（需要支持更多常见格式）**"):
            #     st.session_state.upload_manual_test_cases = not st.session_state.upload_manual_test_cases
            # if st.session_state.upload_manual_test_cases:
            #     manual_test_cases = cols[0].file_uploader("用例上传", type=["xlsx", "txt"])
            #     if manual_test_cases is not None:
            #         if manual_test_cases.name.endswith(".xlsx"):
            #             manual_test_cases = pd.read_excel(manual_test_cases)
            #             formatted = []
            #             headers = " | ".join(manual_test_cases.columns)
            #             formatted.append(headers)
            #             # 添加行数据
            #             for _, row in manual_test_cases.iterrows():
            #                 formatted.append(" | ".join(str(x) for x in row.values))
            #         elif manual_test_cases.name.endswith('.txt'):
            #             # 处理文本文件
            #             manual_test_cases = manual_test_cases.read().decode("utf-8", 'ignore')
            #
            #     manual_case_inputs = cols[0].text_area("人工测试用例",
            #                                            height=200,
            #                                            value=manual_test_cases,
            #                                            placeholder="上传测试用例文件或手动在此填写测试用例"
            #                                            )
            with cols[0].expander(":heart: **上传人工测试用例（可选）（需要支持更多常见格式）**"):
                manual_test_cases = st.file_uploader("用例上传", type=["xlsx", "txt"])
                if manual_test_cases is not None:
                    if manual_test_cases.name.endswith(".xlsx"):
                        manual_test_cases = pd.read_excel(manual_test_cases)
                        formatted = []
                        headers = " | ".join(manual_test_cases.columns)
                        formatted.append(headers)
                        # 添加行数据
                        for _, row in manual_test_cases.iterrows():
                            formatted.append(" | ".join(str(x) for x in row.values))
                    elif manual_test_cases.name.endswith('.txt'):
                        # 处理文本文件
                        manual_test_cases = manual_test_cases.read().decode("utf-8", 'ignore')

                manual_case_inputs = st.text_area("人工测试用例",
                                                       height=200,
                                                       value=manual_test_cases,
                                                       placeholder="上传测试用例文件或手动在此填写测试用例"
                                                       )

            # 上传产品需求文档
            with cols[0].expander(":fire: **PRD配置（必选）**"):
                upload_prd = st.file_uploader("**上传产品需求文档（需要支持更多格式，如带图文档，纯文字文档等）**", type="txt")



if __name__ == "__main__":
    page = Page()
