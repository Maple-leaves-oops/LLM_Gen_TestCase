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
import re
from utils import model_param_section, save_model_config


class Page:
    def __init__(self):
        self.base_init()
        self.css_init()
        self.status_init()
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
    def status_init():
        # 图文解析功能是否开启
        if 'image_analysis' not in st.session_state:
            st.session_state.image_analysis = False

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
            expander3 = st.expander("**相关文档**", False)
            with expander3:
                st.markdown("""
                    <div style="position: fixed; bottom: 10px; width: 100%;">
                        <p><strong>相关文档:</strong></p>
                    </div>
                """, unsafe_allow_html=True)

        pagination_1, pagination_2 = st.tabs([":couple: **功能交互**", ":snowman: **MCP服务**"])

        with pagination_1:
            cols_1 = st.columns([1, 1])

            # 测试用例参数配置
            with cols_1[0].expander(":rose: **测试用例参数配置（可选）**"):
                # 添加测试用例数量控制
                test_case_count_range = st.slider("**生成测试用例数量范围**", help="指定生成的测试用例数量范围",
                                                  min_value=0,
                                                  max_value=100, value=(0, 0), step=1)

            with cols_1[0].expander(
                    ":milky_way:**上传人工测试用例（可选）**"):
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
                # warning: 不要写成：st.session_state.image_analysis =
                # st.checkbox("**启用图文档解析功能**", value=st.session_state.image_analysis)否则复选框要点击两次才生效，
                # 可能和streamlit的状态变量的赋值机制有关，需要调研一下
                st.session_state.image_analysis = st.checkbox("**启用图文档解析功能**",
                                                              value=False)
                # 上传产品需求文档
                upload_prd = st.file_uploader("**上传产品需求文档（需要支持更多格式，如带图文档，纯文字文档等）**",
                                              type="txt")
                if upload_prd:
                    if upload_prd.name.endswith("txt"):
                        upload_prd = upload_prd.read().decode("utf-8", "ignore")
                prd_inputs = st.text_area(
                    "**产品需求文档**",
                    height=200,
                    value=upload_prd,
                    placeholder="请在此详细描述需求"
                )

            # 模型参数配置
            with cols_1[0].expander("**模型参数配置**"):
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

                if st.session_state.image_analysis:
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
                            if st.session_state.image_analysis:
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
                    except Exception as e:
                        st.error(f"配置保存失败！错误信息: {str(e)}")

            # 给编写用例的LLM的提示词
            with cols_1[1].expander(":palm_tree: **编写用例模型提示词（必选）**"):
                with open('./Templates/gen_cases_model_prompt.txt', 'r', encoding='utf-8') as f:
                    gen_cases_model_prompt = f.read()
                gen_cases_model_prompt = st.text_area("**编写用例提示词预览**", height=400,
                                                      value=gen_cases_model_prompt,
                                                      placeholder="need_to_config")
            # 给评审用例的LLM的提示词
            with cols_1[1].expander(":cyclone: **评审用例模型提示词（必选）**"):
                with open('./Templates/review_cases_model_prompt.txt', 'r', encoding='utf-8') as f:
                    review_cases_model_prompt = f.read()
                review_cases_model_prompt = st.text_area("**评审用例提示词预览**", height=400,
                                                         value=review_cases_model_prompt, placeholder="need_to_config")
            if st.session_state.image_analysis:
                # 给文档解析的LLM的提示词
                with cols_1[1].expander(":maple_leaf: **文档解析模型提示词（必选）**"):
                    with open('./Templates/analysis_prd_model_prompt.txt', 'r', encoding='utf-8') as f:
                        analysis_prd_model_prompt = f.read()
                    analysis_prd_model_prompt = st.text_area("**文档解析提示词预览**", height=400,
                                                             value=analysis_prd_model_prompt,
                                                             placeholder="need_to_config")

            button_placeholder = st.empty()
            gen_cases_button = button_placeholder.button("生成测试用例", disabled=False, key="gen_cases_button")

            if gen_cases_button and prd_inputs:
                # task: 需要大模型合作完成的任务
                st.session_state.running_cases_now = True
                button_placeholder.empty()
                button_placeholder.button("生成测试用例", disabled=True, key="gen_cases_button_disabled")

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

                    # # 用来标志对话是否结束，若已经结束，终止词后面的模型输出内容不会再显示
                    # is_continue = True
                    # 模型组开始解决指定任务
                    async for chunk in chat_team.run_stream(task=task):
                        # 存储模型发言时生成的内容
                        content = ""
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
                            # 将新内容添加到完整响应中
                            # if is_continue and content != "" and not content.startswith("TaskResult"):
                            #     response += '\n\n' + content
                            if content != "" and not content.startswith("TaskResult"):
                                response += '\n\n' + content
                            # 更新显示区域
                            response_display.markdown(response)
                            # 若模型发言中输出APPROVE，即意味着对话结束，后续输出内容不会再被记录
                            if content.find("APPROVE") > 0:
                                # is_continue = False
                                break

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

                # 对于需要执行复杂计算或数据处理的函数，使用@st.cache_resource可以避免每次重新计算。
                # 函数的输入相同，返回的结果也会被缓存，以便下次直接使用缓存的结果。
                @st.cache_resource
                def format_testcases(raw_output):
                    cases = re.findall(r'(\|.+\|)', raw_output, re.IGNORECASE)
                    print(dict.fromkeys(cases))
                    new_cases = list(dict.fromkeys(cases))
                    return new_cases

                try:
                    with st.spinner("正在生成测试用例..."):
                        result = asyncio.run(gen_review_testcases())
                        case_list = format_testcases(result)
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

                button_placeholder.empty()

            elif gen_cases_button and not prd_inputs:
                error_message = st.empty()
                error_message.error("输入异常：缺少必要的输入,请提供正确的输入!")
                time.sleep(2)
                error_message.empty()

        with pagination_2:
            st.write("need_todo")


if __name__ == "__main__":
    page = Page()
