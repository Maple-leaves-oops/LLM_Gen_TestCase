#!/usr/bin/python
# -*- coding: utf-8 -*-
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.agents import AssistantAgent
import streamlit.components.v1 as components
from configparser import ConfigParser
from pathlib import Path
import streamlit as st
from io import BytesIO
from llms import *
import xlsxwriter
import platform
import asyncio
import base64
import time
import os
import re
import docx
import pandas as pd
import tempfile
import shutil

# 设置页面配置
st.set_page_config(
    page_title="LLM生成测试用例",
    page_icon=":rocket:",
    layout="wide"
)

conf = ConfigParser()
pt = platform.system()
main_path = os.path.split(os.path.realpath(__file__))[0]
config_path = os.path.join(os.path.split(os.path.realpath(__file__))[0], 'config.ini')


def css_init():
    st.markdown('''<style>
.edw49t12 {
    max-width: none;
    overflow: visible;
    text-overflow: initial;
    white-space: normal;
}
</style>''', unsafe_allow_html=True)


def session_init():
    if 'run_cases' not in st.session_state:
        st.session_state.run_cases = True


def main():
    if pt in ["Windows", "Linux", "Darwin"]:
        session_init()  # session缓存初始化
        css_init()  # 前端css样式初始化
        html_init()  # 前端html布局初始化
    else:
        cs_404()
    return None


def cs_404():
    # 背景图片的网址
    img_url = 'https://img.zcool.cn/community/0156cb59439764a8012193a324fdaa.gif'

    # 修改背景样式
    st.markdown('''<span style="color: cyan"> ''' + f"不支持当前系统 {pt} 运行" + '''</span>''', unsafe_allow_html=True)
    st.markdown('''<style>.css-fg4pbf{background-image:url(''' + img_url + ''');
    background-size:100% 100%;background-attachment:fixed;}</style>''', unsafe_allow_html=True)


def img_to_bytes(img_path):
    img_bytes = Path(os.path.split(os.path.realpath(__file__))[0] + "\\" + img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded


def read_system_message(filename):
    message_path = os.path.join(main_path, filename)
    with open(message_path, "r", encoding="utf8") as f:  # 打开文件
        data = f.read()  # 读取文件
        return data


# 创建测试用例生成器代理
@st.cache_resource
def get_testcase_writer(_mode_client, system_message):
    return AssistantAgent(
        name="testcase_writer",
        model_client=_mode_client,
        system_message=system_message,
        # model_client_stream=True,
    )


# 创建评审用例生成器代理
@st.cache_resource
def get_testcase_reader(_mode_client, system_message):
    return AssistantAgent(
        name="critic",
        model_client=_mode_client,
        system_message=system_message,
        model_client_stream=True,
    )


# 用例格式化
@st.cache_resource
def format_testcases(raw_output):
    cases = re.findall(r'(\|.+\|)', raw_output, re.IGNORECASE)
    new_cases = list(dict.fromkeys(cases))
    return new_cases


def html_init():
    js_code = '''
    $(document).ready(function(){
        $("footer", window.parent.document).remove()
    });
    '''
    # 引用了JQuery v2.2.4
    components.html(f'''<script src="https://cdn.bootcdn.net/ajax/libs/jquery/2.2.4/jquery.min.js"></script>
        <script>{js_code}</script>''', width=0, height=0)

    # sidebar.expander
    with st.sidebar:
        expander1 = st.expander("使用说明", True)
        with expander1:
            st.markdown(
                """
            ### **使用步骤**
            ##### 1、上传文件（.txt .docx）或手动输入需求描述
            ##### 2、设置高级选项设置
            ##### 3、点击"生成测试用例"按钮
            ##### 4、查看生成的测试用例
            ##### 5、下载测试用例文件
            
            ### **高级选项设置**
            ##### **用例分类**：选择用例类型（功能验证用例、边界用例、异常场景用例、性能/兼容性用例、回归测试用例）
            ##### **用例优先级**：设置整体用例的优先级
            """
            , unsafe_allow_html=True)

        st.sidebar.markdown("---")

        expander2 = st.expander("关于", True)
        with expander2:
            st.markdown(
                """
                ###### 本工具使用到的AI工具包括（Doubao、DeepSeek）
                ###### AI工具生成的测试用例可作为参考使用，具体业务还需要人工干预并进行补充
                ###### 本工具是利用Doubao写测试用例，DeepSeek负责用例评审
                """
            )

    # 读取配置
    conf.read(config_path)
    deep_base_url_list = conf['doubao']['base_url_list'].split(",")
    deepseek_base_url_list = conf['deepseek']['base_url_list'].split(",")
    deep_model_list = conf['doubao']['model_list'].split(",")
    deepseek_model_list = conf['deepseek']['model_list'].split(",")
    # main主页面
    source_tab1, source_tab2, source_tab3 = st.tabs(["🧩AI模型设置", "🤖 AI交互", "📄 文档解析"])
    # AI模型设置
    with source_tab1:
        st.subheader("doubao模型配置【编写用例】")
        ai1 = st.checkbox("doubao", eval(conf['doubao']['choice']))
        cols1 = st.columns([2, 2, 2])
        if ai1:
            api_key_1 = cols1[0].text_input("doubao_api_key",
                                            value=conf['doubao']['api_key'])
            base_url_1 = cols1[1].selectbox("base_url", deep_base_url_list[:-1],
                                            index=deep_base_url_list.index(conf['doubao']['base_url']))
            model_1 = cols1[2].selectbox("model", deep_model_list[:-1],
                                         index=deep_model_list.index(conf['doubao']['model']))
            max_tokens_1 = cols1[0].number_input("Doubao最大输出Token:",
                                                 max_value=20480,
                                                 min_value=0,
                                                 value=int(conf['doubao']['tokens']),
                                                 help="1个英文字符 ≈ 0.3 个 token。1 个中文字符 ≈ 0.6 个 token")
            temperature_1 = cols1[1].number_input("Doubao模型随机性参数temperature:",
                                                  max_value=20,
                                                  min_value=0,
                                                  value=int(conf['doubao']['temperature']),
                                                  help="模型随机性参数，数字越大，生成的结果随机性越大，一般为0.7，如果希望AI提供更多的想法，可以调大该数字")
            top_p_1 = cols1[2].number_input("Doubao模型随机性参数top:",
                                            max_value=10,
                                            min_value=0,
                                            value=int(conf['doubao']['top']),
                                            help="模型随机性参数，接近 1 时：模型几乎会考虑所有可能的词，只有概率极低的词才会被排除，随机性也越强；")

        st.subheader("DeepSeek模型配置【评审用例】")
        ai2 = st.checkbox("deepseek", eval(conf['deepseek']['choice']))
        cols2 = st.columns([2, 2, 2])
        if ai2:
            api_key_2 = cols2[0].text_input("deepseek_api_key",
                                            value=conf['deepseek']['api_key'])
            base_url_2 = cols2[1].selectbox("base_url", deepseek_base_url_list[:-1],
                                            index=deepseek_base_url_list.index(conf['deepseek']['base_url']))
            model_2 = cols2[2].selectbox("model", deepseek_model_list[:-1],
                                         index=deepseek_model_list.index(conf['deepseek']['model']))
            max_tokens_2 = cols2[0].number_input("DeepSeek最大输出Token:",
                                                 max_value=20480,
                                                 min_value=0,
                                                 value=int(conf['deepseek']['tokens']),
                                                 help="1个英文字符 ≈ 0.3 个 token。1 个中文字符 ≈ 0.6 个 token")
            temperature_2 = cols2[1].number_input("DeepSeek模型随机性参数temperature:",
                                                  max_value=20,
                                                  min_value=0,
                                                  value=int(conf['deepseek']['temperature']),
                                                  help="模型随机性参数，数字越大，生成的结果随机性越大，一般为0.7，如果希望AI提供更多的想法，可以调大该数字")
            top_p_2 = cols2[2].number_input("DeepSeek模型随机性参数top:",
                                            max_value=10,
                                            min_value=0,
                                            value=int(conf['deepseek']['top']),
                                            help="模型随机性参数，接近 1 时：模型几乎会考虑所有可能的词，只有概率极低的词才会被排除，随机性也越强；")

        if st.button('保存配置'):
            try:
                if ai1:
                    conf['doubao'] = {
                        'choice': ai1,
                        'api_key': api_key_1,
                        'base_url': base_url_1,
                        'model': model_1,
                        'tokens': max_tokens_1,
                        'temperature': temperature_1,
                        'top': top_p_1,
                        'base_url_list': ",".join(deep_base_url_list),
                        'model_list': ",".join(deep_model_list)
                    }
                else:
                    conf['doubao'] = {
                        'choice': ai1,
                        'api_key': conf['doubao']['api_key'],
                        'base_url': conf['doubao']['base_url'],
                        'model': conf['doubao']['model'],
                        'tokens': conf['doubao']['tokens'],
                        'temperature': conf['doubao']['temperature'],
                        'top': conf['doubao']['top'],
                        'base_url_list': conf['doubao']['base_url_list'],
                        'model_list': conf['doubao']['model_list']
                    }
                if ai2:
                    conf['deepseek'] = {
                        'choice': ai2,
                        'api_key': api_key_2,
                        'base_url': base_url_2,
                        'model': model_2,
                        'tokens': max_tokens_2,
                        'temperature': temperature_2,
                        'top': top_p_2,
                        'base_url_list': ",".join(deepseek_base_url_list),
                        'model_list': ",".join(deepseek_model_list)
                    }
                else:
                    conf['deepseek'] = {
                        'choice': ai2,
                        'api_key': conf['deepseek']['api_key'],
                        'base_url': conf['deepseek']['base_url'],
                        'model': conf['deepseek']['model'],
                        'tokens': conf['deepseek']['tokens'],
                        'temperature': conf['deepseek']['temperature'],
                        'top': conf['deepseek']['top'],
                        'base_url_list': conf['deepseek']['base_url_list'],
                        'model_list': conf['deepseek']['model_list']
                    }

                with open(config_path, 'w', encoding='utf-8') as f:
                    conf.write(f)
                with st.spinner('保存中...'):
                    time.sleep(1)
                st.snow()
            except:
                st.error("【接口返回结果检查】输入数据只支持json格式数据")

    # AI交互
    with source_tab2:
        cases_rate_list = [60, 20, 20, 0, 0]
        cols3 = st.columns([2, 2])
        # 页面标题
        cols3[0].markdown("输入你的需求描述，AI 将为你生成相应的测试用例")
        # 高级选项（可折叠）
        with cols3[0].expander("高级选项"):
            show_slider = st.checkbox('用例分类占比(%)', True)
            cols4 = st.columns([2, 2])
            if show_slider:
                functional_testing = cols4[0].slider("功能用例", min_value=0, max_value=100, value=55)
                boundary_testing = cols4[0].slider("边界用例", min_value=0, max_value=100, value=25)
                exception_testing = cols4[0].slider("异常用例", min_value=0, max_value=100, value=20)
                perfmon_testing = cols4[1].slider("性能/兼容性用例", min_value=0, max_value=100, value=0)
                regression_testing = cols4[1].slider("回归测试用例", min_value=0, max_value=100, value=0)
                cases_rate_list = [functional_testing,
                                   boundary_testing,
                                   exception_testing,
                                   perfmon_testing,
                                   regression_testing]
            test_priority = st.selectbox("测试优先级", ["--", "急", "高", "中", "低"], index=0)
            # 添加测试用例数量控制
            test_case_count = st.number_input("生成测试用例数量",
                                              min_value=0,
                                              max_value=200,
                                              value=5,
                                              step=1,
                                              help="指定需要生成的测试用例数量")

        # 上传人工测试用例
        test_cases = cols3[0].file_uploader("上传人工测试用例", type=["xlsx", "txt"])
        if test_cases is not None:
            if test_cases.name.endswith('.xlsx'):
                # 读取Excel文件
                test_cases = pd.read_excel(test_cases)
                # 自定义美化格式
                formatted = []
                # 添加表头
                headers = " | ".join(test_cases.columns)
                formatted.append(headers)

                # 添加行数据
                for _, row in test_cases.iterrows():
                    formatted.append(" | ".join(str(x) for x in row.values))

                test_cases = "\n".join(formatted)
            elif test_cases.name.endswith('.txt'):
                # 处理文本文件
                test_cases = test_cases.read().decode("utf-8", 'ignore')

        # 用户输入区域
        case_input = cols3[0].text_area("人工测试用例",
                                        height=250,
                                        value=test_cases,
                                        placeholder="请输入人工测试用例用于对比")

        # 上传文件
        uploaded_file = cols3[0].file_uploader("上传需求", type=["txt"])
        uploaded_text = ""
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.txt'):
                uploaded_text = uploaded_file.read().decode('utf-8', 'ignore')

        # 用户输入区域
        user_input = cols3[0].text_area("需求描述",
                                        height=250,
                                        value=uploaded_text,
                                        placeholder="请详细描述你的功能需求，例如：\n"
                                                    "开发一个用户注册功能 \n"
                                                    "1、要求用户提供用户名、密码和电子邮件，\n"
                                                    "2、用户名长度为3-20个字符，\n"
                                                    "3、密码长度至少为8个字符且必须包含数字和字母，\n"
                                                    "4、电子邮件必须是有效格式。")

        system_writer_message = read_system_message("TESTCASE_WRITER_SYSTEM_MESSAGE.txt")
        system_reader_message = read_system_message("TESTCASE_READER_SYSTEM_MESSAGE.txt")
        tester_system_message = system_writer_message.replace("{{functional_testing}}", str(cases_rate_list[0]))\
            .replace("{{boundary_testing}}", str(cases_rate_list[1]))\
            .replace("{{exception_testing}}", str(cases_rate_list[2]))\
            .replace("{{perfmon_testing}}", str(cases_rate_list[3]))\
            .replace("{{regression_testing}}", str(cases_rate_list[4]))
        # 消息模板
        message_tab1, message_tab2 = cols3[1].tabs(["✍执行", "🔍 审核"])
        with message_tab1:
            customer_system_message = st.text_area("👉消息模板预览", height=480, value=tester_system_message)
        with message_tab2:
            customer_reader_message = st.text_area("👉消息模板预览", height=480, value=system_reader_message)
        # 调整模型参数
        model_doubao_info["parameters"]["max_tokens"] = int(conf['doubao']['tokens'])
        model_doubao_info["parameters"]["temperature"] = int(conf['doubao']['temperature']) / 10
        model_doubao_info["parameters"]["top_p"] = int(conf['doubao']['top']) / 10
        model_deepseek_info["parameters"]["max_tokens"] = int(conf['deepseek']['tokens'])
        model_deepseek_info["parameters"]["temperature"] = int(conf['deepseek']['temperature']) / 10
        model_deepseek_info["parameters"]["top_p"] = int(conf['deepseek']['top']) / 10

        # 提交按钮
        submit_button = cols3[0].button("生成测试用例")
        if submit_button:
            if bool(st.session_state.run_cases):
                st.session_state.update({"run_cases": False})
                # 处理提交
                if user_input:
                    # 准备任务描述
                    if test_priority != "--" and test_case_count != 0:
                        task = f""" 
                        需求描述: {user_input}
                        测试优先级: {test_priority}
                        【重要】请生成 {test_case_count} 条测试用例，不允许少。
                        评审需要对比的人工测试用例：{case_input}
                        """
                    elif test_case_count == 0 and test_priority != "--":
                        task = f""" 
                        需求描述: {user_input}
                        测试优先级: {test_priority}
                        评审需要对比的人工测试用例：{case_input}
                        """
                    elif test_case_count != 0 and test_priority == "--":
                        task = f""" 
                        需求描述: {user_input}
                        【重要】请生成 {test_case_count} 条测试用例，不允许少。
                        评审需要对比的人工测试用例：{case_input}
                        """
                    else:
                        task = f""" 
                        需求描述: {user_input}
                        评审需要对比的人工测试用例：{case_input}
                        """

                    # 创建一个固定的容器用于显示生成内容
                    response_container = st.container()

                    # 多角色参与生成用例
                    async def m_roles_generate_testcases():
                        full_response = ""
                        doubao_response = ""
                        is_continue = True
                        text_termination = TextMentionTermination("APPROVE")
                        model_doubao_client = OpenAIChatCompletionClient(
                            model=conf['doubao']['model'],
                            base_url=conf['doubao']['base_url'],
                            api_key=conf['doubao']['api_key'],
                            model_info=model_doubao_info,
                        )
                        testcase_writer = get_testcase_writer(model_doubao_client, customer_system_message)
                        model_deepseek_client = OpenAIChatCompletionClient(
                            model=conf['deepseek']['model'],
                            base_url=conf['deepseek']['base_url'],
                            api_key=conf['deepseek']['api_key'],
                            model_info=model_deepseek_info,
                        )
                        testcase_reader = get_testcase_reader(model_deepseek_client, customer_reader_message)
                        team = RoundRobinGroupChat(
                            participants=[testcase_writer, testcase_reader],
                            termination_condition=text_termination,
                            max_turns=10
                        )
                        # 创建一个空元素用于更新内容
                        with response_container:
                            placeholder = st.empty()
                        async for chunk in team.run_stream(task=task):
                            content = ""
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
                                if is_continue and content != "" and not content.startswith("TaskResult"):
                                    full_response += '\n\n' + content
                                    # 追加doubao_response
                                    if hasattr(chunk, 'participant_name') and chunk.participant_name == \
                                            'testcase_writer':
                                        doubao_response += content
                                # 更新显示区域（替换而非追加）
                                placeholder.markdown(full_response)
                                # APPROVE结束退出
                                if content.find("APPROVE") > 0:
                                    is_continue = False

                        return full_response, doubao_response

                    # 单角色参与生成用例
                    async def s_roles_generate_testcases():
                        full_response = ""
                        doubao_response = ""
                        is_continue = True
                        text_termination = TextMentionTermination("APPROVE")
                        model_doubao_client = OpenAIChatCompletionClient(
                            model=conf['doubao']['model'],
                            base_url=conf['doubao']['base_url'],
                            api_key=conf['doubao']['api_key'],
                            model_info=model_doubao_info,
                            timeout=1800,
                        )
                        testcase_writer = get_testcase_writer(model_doubao_client, customer_system_message)
                        team = RoundRobinGroupChat(
                            participants=[testcase_writer],
                            termination_condition=text_termination,
                            max_turns=1
                        )
                        # 创建一个空元素用于更新内容
                        with response_container:
                            placeholder = st.empty()
                        async for chunk in team.run_stream(task=task):
                            content = ""
                            if chunk:
                                # 处理不同类型的chunk
                                if hasattr(chunk, 'content'):
                                    if chunk.type != 'ModelClientStreamingChunkEvent':
                                        content = chunk.content
                                elif isinstance(chunk, str):
                                    content = chunk
                                else:
                                    content = str(chunk)
                                # 将新内容添加到完整响应中
                                if is_continue and content != "" and not content.startswith("TaskResult"):
                                    full_response += '\n\n' + content
                                    # 替换 doubao_response
                                    if hasattr(chunk,
                                               'participant_name') and chunk.participant_name == 'doubao_writer':
                                        doubao_response += content
                                # 更新显示区域（替换而非追加）
                                placeholder.markdown(full_response)
                                # APPROVE结束退出
                                if content.find("APPROVE") > 0:
                                    is_continue = False

                        return full_response, doubao_response

                    # 重新拉取消息
                    def show_message(message):
                        case_list_new = format_testcases(message)
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

                    if eval(conf['doubao']['choice']) and eval(conf['deepseek']['choice']):
                        if conf['doubao']['api_key'] != "" and conf['deepseek']['api_key'] != "":
                            try:
                                with st.spinner("正在生成测试用例..."):
                                    result, doubao_result = asyncio.run(m_roles_generate_testcases())
                                    case_list = format_testcases(result)
                                    doubao_case_list = format_testcases(doubao_result)
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
                                                        worksheet.write(row-1, col-1, str(cell).strip())
                                                    else:
                                                        worksheet.write(row, col-1, str(cell).strip())
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
                        else:
                            st.error("请先配置doubao/deepseek模型的APIKEY!")
                    elif eval(conf['doubao']['choice']) and not eval(conf['deepseek']['choice']):
                        if conf['doubao']['api_key'] != "":
                            try:
                                with st.spinner("正在生成测试用例..."):
                                    result = asyncio.run(s_roles_generate_testcases())
                                    case_list = format_testcases(result[0])
                                st.success("✅ 测试用例生成完成!")
                                if len(case_list):
                                    st.download_button(
                                        label="下载测试用例(.md)",
                                        data="\n".join(case_list),
                                        file_name="测试用例.md",
                                        mime="text/markdown",
                                        icon=":material/markdown:",
                                        on_click=show_message,
                                        args=(result[0],),
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
                                        args=(result[0],),
                                    )
                            except Exception as e:
                                st.error(f"生成测试用例时出错: {str(e)}")
                        else:
                            st.error("请先配置doubao模型的APIKEY!")
                    else:
                        st.error("请先配置doubao模型并选中保存!")
                    st.session_state.update({"run_cases": True})

                elif submit_button and not user_input:
                    st.error("请输入需求描述")
                    st.session_state.update({"run_cases": True})
            else:
                st.warning("正在生成测试用例中，请不要频繁操作！")
    
    # 文档解析功能
    with source_tab3:
        try:
            from document_integration import DocumentIntegration
            
            # 初始化文档集成
            if 'doc_integration' not in st.session_state:
                st.session_state.doc_integration = DocumentIntegration()
            
            # 渲染文档解析功能
            st.session_state.doc_integration.render_document_upload_section()
            
        except ImportError as e:
            st.error(f"文档解析模块导入失败: {e}")
            st.info("请确保已安装所需的依赖包：PyMuPDF, Pillow, opencv-python, numpy")
        except Exception as e:
            st.error(f"文档解析功能初始化失败: {e}")
    
    return None


if __name__ == '__main__':
    main()
