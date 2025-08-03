from io import BytesIO
import streamlit as st
import pandas as pd
import json
import time
import xlsxwriter
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
import asyncio


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
        # TODO 计划增加带图文档解析功能，若选择该功能,st.session_state.image_analysis设置为True，走不同的流程
        # TODO 状态变量的初始化建议单独写个函数来完成，比如status_init
        if 'image_analysis' not in st.session_state:
            st.session_state.no_image_analysis = False

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

        pagination_1, pagination_2, pagination_3 = st.tabs([":couple: **功能交互**", ":two_men_holding_hands: **模型设置**",
                                                            ":two_women_holding_hands: **MCP服务**"])

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

            api_key = cols_2[0].text_input(f"api_key", value=conf["api_key"],
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
                                                value=conf["model_info"]["parameters"]["max_tokens"],
                                                help=f"最大值：4096；最小值：0",
                                                key=f"{key_prefix}_max_tokens")
            temperature = cols_2[1].number_input(f"{model}模型随机性参数temperature:",
                                                 max_value=1.0,
                                                 min_value=0.0,
                                                 value=conf["model_info"]["parameters"]["temperature"],
                                                 help="模型随机性参数，数字越大，生成的结果随机性越大，一般为0.7，如果希望AI提供更多的想法，可以调大该数字",
                                                 key=f"{key_prefix}_temperature")
            top_p = cols_2[2].number_input(f"{model}模型随机性参数top:",
                                           max_value=1.0,
                                           min_value=0.0,
                                           value=conf["model_info"]["parameters"]["top_p"],
                                           help="模型随机性参数，接近 1 时：模型几乎会考虑所有可能的词，只有概率极低的词才会被排除，随机性也越强；",
                                           key=f"{key_prefix}_top_p")

            return [api_key, base_url, model, max_tokens, temperature,
                    top_p, conf["base_url_list"], conf["model_list"], model_select]

        # 定义一个函数来保存模型参数设置
        def save_model_config(config_dict, filepath, model_select, api_key, base_url, model, base_url_list,
                              model_list, max_tokens, temperature, top_p):
            config_dict[model_select] = {
                'api_key': api_key,
                'base_url': base_url,
                'model': model,
                'base_url_list': base_url_list,
                'model_list': model_list,
                "model_info": {
                    "name": "deepseek-chat",
                    "parameters": {
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p
                    },
                    "family": "deepseek",
                    "functions": [],
                    "vision": False,
                    "json_output": True,
                    "function_calling": True,
                    "structured_output": True
                }
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4)

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
                        save_model_config(
                            gen_cases_model_config,
                            "./Templates/gen_cases_model_config.json",
                            model_select_1, api_key_1, base_url_1, model_1,
                            base_url_list_1, model_list_1,
                            max_tokens_1, temperature_1, top_p_1
                        )

                        save_model_config(
                            review_cases_model_config,
                            "./Templates/review_cases_model_config.json",
                            model_select_2, api_key_2, base_url_2, model_2,
                            base_url_list_2, model_list_2,
                            max_tokens_2, temperature_2, top_p_2
                        )
                        if not st.session_state.no_image_analysis:
                            save_model_config(
                                analysis_prd_model_config,
                                "./Templates/analysis_prd_model_config.json",
                                model_select_3, api_key_3, base_url_3, model_3,
                                base_url_list_3, model_list_3,
                                max_tokens_3, temperature_3, top_p_3
                            )
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
            st.write("need_todo")

        with pagination_1:
            cols_1 = st.columns([1, 1])

            # 测试用例参数配置
            with cols_1[0].expander(":rose: **测试用例参数配置（可选）**"):
                # 添加测试用例数量控制
                test_case_count_range = st.slider("**生成测试用例数量范围**", help="指定生成的测试用例数量范围", min_value=0,
                                                  max_value=100, value=(0, 0), step=1)
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
            with cols_1[0].expander(":milky_way:**上传人工测试用例（可选）（需要支持更多常见格式）(如何完成和人工用例的对比，如何设计指标来对比，need_todo)**"):
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

            gen_cases_button = cols_1[0].button("生成测试用例")
            # # 该状态变量用来标识是否正在执行生成测试用例的任务
            # if 'running_cases_now' not in st.session_state:
            #     st.session_state.running_cases_now = False
            if gen_cases_button and prd_inputs:
                # task:需要大模型合作完成的任务
                # TODO （如何完成和人工用例的对比，如何设计指标来对比，need_todo）
                # TODO 需要把异常改成提示，而不是报错
                # if not st.session_state.running_cases_now:
                #     st.session_state.running_cases_now = True
                    if test_case_count_range != (0, 0):
                        task = f"""
                        需求描述：{prd_inputs}
                        【重要】：最少生成{test_case_count_range[0]}条用例，最多生成{test_case_count_range[1]}条用例
                        """
                    else:
                        task = f"""
                        需求描述：{prd_inputs}
                        """

                    # 模型输出内容的显示区域
                    response_container = st.container()

                    # 生成并评审用例
                    async def gen_review_testcases():
                        # 接受模型回复的内容
                        response = ""
                        termination_condition = TextMentionTermination("APPROVE")
                        # 创建生成测试用例的补全式的对话客户端
                        # TODO 注意：model_select_1是生成测试用例时选择的模型名，model_select_2是评审测试用例时选择的模型名，
                        #  model_select_3是图文解析时选择的模型名，后续会更改这三个命名，显得更加直观
                        # TODO json格式的数据不支持注释，计划用yaml文件来替代该配置
                        # 1.模型调用
                        gen_cases_model = OpenAIChatCompletionClient(
                            model=gen_cases_model_config[model_select_1]['model'],
                            base_url=gen_cases_model_config[model_select_1]['base_url'],
                            api_key=gen_cases_model_config[model_select_1]['api_key'],
                            model_info=gen_cases_model_config[model_select_1]["model_info"],
                        )
                        # 2.agent抽象
                        gen_cases_model = AssistantAgent(name="gen_cases_model", model_client=gen_cases_model,
                                                         system_message=gen_cases_model_prompt)
                        # 创建评审测试用例的补全式的对话客户端
                        review_cases_model = OpenAIChatCompletionClient(
                            model=review_cases_model_config[model_select_2]['model'],
                            base_url=review_cases_model_config[model_select_2]['base_url'],
                            api_key=review_cases_model_config[model_select_2]['api_key'],
                            model_info=review_cases_model_config[model_select_2]["model_info"],
                        )
                        review_cases_model = AssistantAgent(name="review_cases_model", model_client=review_cases_model,
                                                            system_message=review_cases_model_prompt)
                        # 创建对话组
                        chat_team = RoundRobinGroupChat(
                            participants=[gen_cases_model, review_cases_model],
                            termination_condition=termination_condition,
                            max_turns=10,
                        )

                        # 创建一个空元素用于更新内容
                        with response_container:
                            # st.empty() 是一个占位符，只能显示当前一次的内容
                            response_display = st.empty()

                        # 模型组开始解决指定任务
                        async for chunk in chat_team.run_stream(task=task):
                            # 存储模型发言时生成的内容
                            content = ""
                            # 用来标志对话是否结束，若已经结束，终止词后面的模型输出内容不会再显示
                            is_continue = True
                            # chunk有好几种返回对象
                            # TODO 具体有哪些类别需要再研究下
                            if chunk:
                                # 处理不同类型的chunk
                                if hasattr(chunk, 'content') and hasattr(chunk, 'type'):
                                    if chunk.type != 'ModelClientStreamingChunkEvent':
                                        content = chunk.content
                                elif isinstance(chunk, str):
                                    content = chunk
                                else:
                                    content = str(chunk)
                                print(content)
                                # 将新内容添加到完整响应中
                                if is_continue and content != "" and not content.startswith("TaskResult"):
                                    response += '\n\n' + content
                                # 更新显示区域
                                response_display.markdown(response)
                                # 若模型发言中输出APPROVE，即意味着对话结束，后续输出内容不会再被记录
                                if content.find("APPROVE") >= 0:
                                    is_continue = False
                        # 返回模型的所有输出结果
                        return response

                    # 重新拉取消息
                    def show_message(message):
                        case_list_new = message
                        with response_container:
                            placeholder = st.empty()
                            placeholder.markdown(message)
                            st.success("✅ 测试用例生成完成!")
                            st.download_button(
                                label="下载测试用例(.md)",
                                data="\n".join(case_list_new),
                                file_name="测试用例.md",
                                mime="text/markdown",
                                icon=":material/markdown:",
                            )

                            st.download_button(
                                label="下载测试用例(.xlsx)",
                                data=output.getvalue(),
                                file_name="测试用例.xlsx",
                                mime="application/vnd.ms-excel",
                                icon=":material/download:",
                            )

                    # TODO 现在输出格式非常混乱，需要调整
                    try:
                        with st.spinner("正在生成测试用例..."):
                            result = asyncio.run(gen_review_testcases())
                            case_list = result
                        st.success("✅ 测试用例生成完成!")
                        if len(case_list):
                            st.download_button(
                                label="下载测试用例(.md)",
                                data="\n".join(case_list),
                                file_name="测试用例.md",
                                mime="text/markdown",
                                icon=":material/markdown:",
                                on_click=show_message,
                                args=(result,),
                            )
                            output = BytesIO()
                            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                            worksheet = workbook.add_worksheet()
                            for row, case in enumerate(case_list):
                                if case.find("--------") < 0:
                                    for col, cell in enumerate(case.split("|")):
                                        if col > 0:
                                            if row > 1:
                                                worksheet.write(row - 1, col - 1, str(cell).strip())
                                            else:
                                                worksheet.write(row, col - 1, str(cell).strip())
                            workbook.close()
                            st.download_button(
                                label="下载测试用例(.xlsx)",
                                data=output.getvalue(),
                                file_name="测试用例.xlsx",
                                mime="application/vnd.ms-excel",
                                icon=":material/download:",
                                on_click=show_message,
                                args=(result,),
                            )
                    except Exception as e:
                        st.error(f"生成测试用例时出错: {str(e)}")

                    # st.session_state.running_cases_now = False
                # TODO 现在的问题是重复点击生成按钮，会显示提示，但之后就会报错，模型的返回值也不会再次显示了
                # TODO 问题根因是点击了生成按钮，又重开了新的对话，但是之前的对话其实还在进行，就会发生错误，需要想办法解决
                # TODO 现在先注释掉了生成状态这块内容，先考虑怎么解决之前的遗留对话问题吧
                # else:
                #     warning_message = st.empty()
                #     warning_message.warning("正常生成测试用例，请不要重复点击！")
                #     time.sleep(2)
                #     warning_message.empty()
            # TODO 需要调整下其他的必选值，有的其实是有默认值的，但用户把提示词默认值都删了，然后去生成用例的这种情况需要考虑
            elif gen_cases_button and not prd_inputs:
                error_message = st.empty()
                error_message.error("输入异常：缺少必要的输入,请提供正确的输入!")
                time.sleep(2)
                error_message.empty()

        st.markdown("""
            <div style="position: fixed; bottom: 10px; width: 100%;">
                <p><strong>相关文档:</strong></p>
            </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    page = Page()
