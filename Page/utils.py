import streamlit as st
import json


# 定义一个函数来处理模型参数设置
# 当多个控件具有相同的标签或默认值时，它们会被认为是重复的，所以为每个st控件添加一个唯一的key_prefix参数，避免冲突。
def model_param_section(title, config_value, col_widths=None, key_prefix="", model_select="deepseek"):
    # 加载特定模型配置，默认为deepseek
    conf = config_value[model_select]

    if col_widths is None:
        col_widths = [1, 1, 1]
    images_dict = {"param_1": ":sparkles:", "param_2": ":dizzy:", "param_3": ":star2:", }
    st.markdown(f"**{images_dict[key_prefix]} {title}**")
    cols_2 = st.columns(col_widths)

    api_key = cols_2[0].text_input(f"api_key", value=conf["api_key"],
                                   help="输入模型的api_key", key=f"{key_prefix}_api_key")
    base_url = cols_2[1].selectbox("base_url", options=conf["base_url_list"], index=0,
                                   help="输入模型的api接口地址",
                                   key=f"{key_prefix}_base_url")
    model = cols_2[2].selectbox("model", conf["model_list"], index=0,
                                help="选择模型来完成该部分任务",
                                key=f"{key_prefix}_model")
    max_tokens = cols_2[0].number_input(f"{model}-max_tokens:",
                                        max_value=4096,
                                        min_value=0,
                                        value=conf["model_info"]["parameters"]["max_tokens"],
                                        help=f"最大值：4096；最小值：0",
                                        key=f"{key_prefix}_max_tokens")
    temperature = cols_2[1].number_input(f"{model}-temperature:",
                                         max_value=1.0,
                                         min_value=0.0,
                                         value=conf["model_info"]["parameters"]["temperature"],
                                         help="模型随机性参数，数字越大，生成的结果随机性越大，一般为0.7，如果希望AI提供更多的想法，可以调大该数字",
                                         key=f"{key_prefix}_temperature")
    top_p = cols_2[2].number_input(f"{model}-top:",
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
