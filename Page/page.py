import streamlit as st
import os
import pandas as pd
import json
import time


class Page:
    def __init__(self):
        self.base_init()
        self.css_init()
        self.html__init()

    @staticmethod
    def base_init():
        st.set_page_config(
            page_title="LLM生成测试用例",
            page_icon=":robot:",
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

        pagination_1, pagination_2, pagination_3 = st.tabs(["功能交互", "模型设置", "MCP服务"])

        with pagination_1:
            cols_1 = st.columns([1, 1])

            # 测试用例参数配置
            with cols_1[0].expander(":rose: **测试用例参数配置（可选）**"):
                # 添加测试用例数量控制
                test_case_count_range = st.slider("**生成测试用例数量范围**", help="指定生成的测试用例数量范围", min_value=0,
                                                  max_value=100, value=(5, 10), step=1)
            # 支持上传人工测试用例用于对比
            # upload_manual_test_cases = cols_1[0].checkbox(":heart: **上传人工测试用例（需要支持更多常见格式）**", False)
            # st.session_state是Streamlit提供的一个机制，用于存储和共享应用中的状态（如变量值），
            # 从而在不同的交互和页面刷新之间保持数据的持续性，一些状态值（动态变化）都推荐使用st.session_state来控制
            # if 'upload_manual_test_cases' not in st.session_state:
            #     st.session_state.upload_manual_test_cases = False
            # if cols_1[0].button(":heart: **上传人工测试用例（可选）（需要支持更多常见格式）**"):
            #     st.session_state.upload_manual_test_cases = not st.session_state.upload_manual_test_cases
            # if st.session_state.upload_manual_test_cases:
            #     manual_test_cases = cols_1[0].file_uploader("用例上传", type=["xlsx", "txt"])
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
            #     manual_case_inputs = cols_1[0].text_area("人工测试用例",
            #                                            height=200,
            #                                            value=manual_test_cases,
            #                                            placeholder="上传测试用例文件或手动在此填写测试用例"
            #                                            )
            with cols_1[0].expander(":milky_way:**上传人工测试用例（可选）（需要支持更多常见格式）**"):
                manual_test_cases = st.file_uploader("**用例上传**", type=["xlsx", "txt"])
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

                manual_case_inputs = st.text_area(
                    "**人工测试用例**",
                    height=200,
                    value=manual_test_cases,
                    placeholder="上传测试用例文件或手动在此填写测试用例"
                )

            # 上传产品需求文档
            with cols_1[0].expander(":fire: **PRD配置（必选）**"):
                # TODO 计划增加带图文档解析功能，若选择该功能,st.session_state.image_analysis设置为True，走不同的流程
                if 'image_analysis' not in st.session_state:
                    st.session_state.no_image_analysis = False
                # if st.button("启用图文档解析功能"):
                #     st.session_state.image_analysis = True
                #     st.success("图文档解析功能已启用！")
                # if st.button("禁用图文档解析功能"):
                #     st.session_state.image_analysis = False
                #     st.success("图文档解析功能已禁用！")
                # if st.checkbox("**启用图文档解析功能**", False, ):
                #     st.session_state.image_analysis = not st.session_state.image_analysis
                # 很奇怪，只有这样子才能实现实时交互，上面的方法都有延迟，必须要点击两下checkbox才会产生状态变化
                st.session_state.no_image_analysis = not st.checkbox("**启用图文档解析功能**",
                                                                     value=st.session_state.no_image_analysis)
                # 上传产品需求文档
                upload_prd = st.file_uploader("**上传产品需求文档（需要支持更多格式，如带图文档，纯文字文档等）**", type="txt")
                if upload_prd:
                    if upload_prd.name.endswith("txt"):
                        upload_prd = upload_prd.read().decode("utf-8", "ignore")
                prd_inputs = st.text_area(
                    "**产品需求文档**",
                    height=200,
                    value=upload_prd,
                    placeholder="请在此详细描述需求"
                )

            # 给编写用例的LLM的提示词
            with cols_1[1].expander(":palm_tree: **编写用例模型提示词（必选）**"):
                with open('./Templates/gen_cases_model_prompt.txt', 'r', encoding='utf-8') as f:
                    gen_cases_model_prompt = f.read()
                gen_cases_model_prompt = st.text_area("**编写用例提示词预览**", height=400, value=gen_cases_model_prompt,
                                                      placeholder="need_to_config")
            # 给评审用例的LLM的提示词
            with cols_1[1].expander(":cyclone: **评审用例模型提示词（必选）**"):
                with open('./Templates/review_cases_model_prompt.txt', 'r', encoding='utf-8') as f:
                    review_cases_model_prompt = f.read()
                review_cases_model_prompt = st.text_area("**评审用例提示词预览**", height=400,
                                                         value=review_cases_model_prompt, placeholder="need_to_config")
            if not st.session_state.no_image_analysis:
                # 给文档解析的LLM的提示词
                with cols_1[1].expander(":maple_leaf: **文档解析模型提示词（必选）**"):
                    with open('./Templates/analysis_prd_model_prompt.txt', 'r', encoding='utf-8') as f:
                        analysis_prd_model_prompt = f.read()
                    analysis_prd_model_prompt = st.text_area("**文档解析提示词预览**", height=400,
                                                             value=analysis_prd_model_prompt,
                                                             placeholder="need_to_config")

            # 定义一个函数来处理模型参数设置
            # TODO 参数需要根据yaml（暂定）配置文件来设置，包括index参数
            # 当多个控件具有相同的标签或默认值时，它们会被认为是重复的，所以为每个st控件添加一个唯一的key_prefix参数，避免冲突。
            def model_param_section(title, config_value, col_widths=None, key_prefix="", model_select="deepseek"):
                # 加载特定模型配置，默认为deepseek
                conf = config_value[model_select]

                if col_widths is None:
                    col_widths = [1, 1, 1]
                images_dict = {"param_1": ":sparkles:", "param_2": ":dizzy:", "param_3": ":star2:", }
                # subheader好像不支持markdown解析
                # st.subheader(":maple_leaf:" + title)
                st.markdown(f"### {images_dict[key_prefix]} {title}")
                cols_2 = st.columns(col_widths)

                api_key = cols_2[0].text_input(f"{model_select}_api_key", value=conf["api_key"],
                                               help="输入模型的api_key", key=f"{key_prefix}_api_key")
                base_url = cols_2[1].selectbox("base_url", options=conf["base_url_list"], index=0,
                                               help="输入模型的api接口地址",
                                               key=f"{key_prefix}_base_url")
                model = cols_2[2].selectbox("model", conf["model_list"], index=0,
                                            help="选择模型来完成该部分任务",
                                            key=f"{key_prefix}_model")
                max_tokens = cols_2[0].number_input(f"{model}最大输出Token:",
                                                    max_value=4096,
                                                    min_value=0,
                                                    value=conf["tokens"],
                                                    help=f"最大值：4096；最小值：0",
                                                    key=f"{key_prefix}_max_tokens")
                temperature = cols_2[1].number_input(f"{model}模型随机性参数temperature:",
                                                     max_value=1.0,
                                                     min_value=0.0,
                                                     value=conf["temperature"],
                                                     help="模型随机性参数，数字越大，生成的结果随机性越大，一般为0.7，如果希望AI提供更多的想法，可以调大该数字",
                                                     key=f"{key_prefix}_temperature")
                top_p = cols_2[2].number_input(f"{model}模型随机性参数top:",
                                               max_value=1.0,
                                               min_value=0.0,
                                               value=conf["top"],
                                               help="模型随机性参数，接近 1 时：模型几乎会考虑所有可能的词，只有概率极低的词才会被排除，随机性也越强；",
                                               key=f"{key_prefix}_top_p")

                return [api_key, base_url, model, max_tokens, temperature,
                        top_p, conf["base_url_list"], conf["model_list"], model_select]

            with pagination_2:
                # 注意，当前的工作目录是run.py所在的目录
                with open("./Templates/gen_cases_model_config.json", 'r') as f:
                    gen_cases_model_config = json.load(f)
                with open("./Templates/review_cases_model_config.json", 'r') as f:
                    review_cases_model_config = json.load(f)

                api_key_1, base_url_1, model_1, max_tokens_1, temperature_1, top_p_1, base_url_list_1, model_list_1, model_select_1 = model_param_section(
                    "编写用例模型参数设置（更多参数等待探索）", key_prefix="param_1", config_value=gen_cases_model_config
                )

                api_key_2, base_url_2, model_2, max_tokens_2, temperature_2, top_p_2, base_url_list_2, model_list_2, model_select_2 = model_param_section(
                    "评审用例模型参数设置", key_prefix="param_2", config_value=review_cases_model_config
                )

                if not st.session_state.no_image_analysis:
                    with open("./Templates/analysis_prd_model_config.json", 'r') as f:
                        analysis_prd_model_config = json.load(f)
                    api_key_3, base_url_3, model_3, max_tokens_3, temperature_3, top_p_3, base_url_list_3, model_list_3, model_select_3 = model_param_section(
                        "文档解析模型参数设置", key_prefix="param_3", config_value=analysis_prd_model_config
                    )

                # 保存的配置信息去覆盖原json配置中的内容
                if st.button("保存配置"):
                    try:
                        with st.spinner("保存中..."):
                            gen_cases_model_config[model_select_1] = {'api_key': api_key_1, 'base_url': base_url_1,
                                                                      'model': model_1, 'tokens': max_tokens_1,
                                                                      'temperature': temperature_1, 'top': top_p_1,
                                                                      'base_url_list': base_url_list_1,
                                                                      'model_list': model_list_1, }
                            review_cases_model_config[model_select_2] = {'api_key': api_key_2, 'base_url': base_url_2,
                                                                         'model': model_2, 'tokens': max_tokens_2,
                                                                         'temperature': temperature_2, 'top': top_p_2,
                                                                         'base_url_list': base_url_list_2,
                                                                         'model_list': model_list_2, }
                            with open("./Templates/gen_cases_model_config.json", 'w') as f:
                                json.dump(gen_cases_model_config, f, indent=4)
                            with open("./Templates/review_cases_model_config.json", 'w') as f:
                                json.dump(review_cases_model_config, f, indent=4)
                            if not st.session_state.no_image_analysis:
                                analysis_prd_model_config[model_select_3] = {'api_key': api_key_3, 'base_url': base_url_3,
                                                             'model': model_3, 'tokens': max_tokens_3,
                                                             'temperature': temperature_3, 'top': top_p_3,
                                                             'base_url_list': base_url_list_3,
                                                             'model_list': model_list_3, }
                                with open("./Templates/analysis_prd_model_config.json", 'w') as f:
                                    json.dump(analysis_prd_model_config, f, indent=4)
                        success_message = st.empty()
                        success_message.success("配置已成功保存！")
                        st.balloons()
                        time.sleep(2)
                        success_message.empty()
                    except FileNotFoundError as e:
                        st.error(f"文件未找到: {e}")
                    except PermissionError as e:
                        st.error(f"权限错误: {e}")
                    except json.JSONDecodeError as e:
                        st.error(f"JSON 解码错误: {e}")
                    except Exception as e:
                        st.error(f"配置保存失败！错误信息: {str(e)}")

            with pagination_3:
                st.write("需要谋划")


if __name__ == "__main__":
    page = Page()
