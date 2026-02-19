# -*- coding: utf-8 -*-
"""
飞行员航班任务准备工具 - 副驾驶专用
Streamlit 应用（个人资质 + 航班概况，共用数据库）

版本升级说明：
- 优化了代码结构和可读性
- 增强了错误处理机制
- 改进了用户交互体验
- 规范了文档生成格式
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Optional, Any

from db_helper import (
    init_db,
    get_profile,
    save_profile,
    update_last_pf_time,
    list_airports,
    get_risks_for_route,
    get_notams_for_route,
    add_or_update_airport,
    delete_airport,
    get_flight_by_number,
    list_flights,
    add_or_update_flight,
    delete_flight,
)

st.set_page_config(page_title="飞行员航班任务准备工具", page_icon="✈️", layout="wide")

# 全局CSS：彻底取消宽度限制，让编辑区铺满屏幕（含“编辑机场信息”）
st.markdown("""
<style>
/* 1. 主容器直接拉满视口 */
[data-testid="stAppViewContainer"] > section,
[data-testid="stAppViewContainer"] > section > div,
.main .block-container {
    max-width: 100% !important;
    width: 100% !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}
/* 2. 取消 Streamlit 默认的内容区最大宽度（约 704px/730px），这是编辑区变窄的根源 */
.main [data-testid="stVerticalBlock"],
.main [data-testid="stHorizontalBlock"],
.main .element-container,
.main .stExpander,
.main section[data-testid="stExpander"] {
    max-width: none !important;
    width: 100% !important;
}
.main .stExpander > div,
.main .stExpander > div > div,
.main section[data-testid="stExpander"] > div,
.main section[data-testid="stExpander"] > div > div {
    max-width: none !important;
    width: 100% !important;
}
.main .stExpander [data-testid="stVerticalBlock"],
.main .stExpander [data-testid="stHorizontalBlock"],
.main .stExpander .element-container,
.main section[data-testid="stExpander"] [data-testid="stVerticalBlock"],
.main section[data-testid="stExpander"] [data-testid="stHorizontalBlock"],
.main section[data-testid="stExpander"] .element-container {
    max-width: none !important;
    width: 100% !important;
}
/* 3. 输入框、文本框占满父容器 */
.stTextInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
.stTextArea textarea { min-height: 4rem !important; }
.stColumn, .stColumn > div,
[data-testid="stForm"],
[data-testid="stHorizontalBlock"] {
    max-width: none !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# 内置默认值（未从数据库加载时使用）
DEFAULTS = {
    "name": "吴帮帮",
    "radio_qual": "无",
    "total_landings": 500,
    "total_hours": 3445.0,
    "type_landings": 450,
    "type_hours": 3200.0,
    "previous_aircraft": "无",
    "app_alert": "无",
    "efb_status": "电量充足，已更新",
    "landing_quality": "正常",
    "pickup_location": "自行前往公司",
    "last_pf_time": "",
}

if "generated_doc" not in st.session_state:
    st.session_state.generated_doc = None

# 从数据库合并默认值
profile = get_profile()
def _d(key):
    if profile and profile.get(key) is not None and str(profile.get(key)).strip() != "":
        return profile[key]
    return DEFAULTS.get(key, "" if key != "last_pf_time" else "")

st.title("✈️ 飞行员航班任务准备工具")
st.caption("专为副驾驶设计")

# 使用 tabs 分隔两个部分
tab_qual, tab_flight, tab_db = st.tabs(["📋 个人资质", "🛫 航班概况", "🗄️ 数据库管理"])

with tab_qual:
    st.header("个人资质")
    col1, col2, col3 = st.columns(3)

    with col1:
        co_pilot_name = st.text_input("姓名", value=_d("name"), key="name")
        TECH_LEVELS = ["A类副驾驶", "B类副驾驶", "C类副驾驶", "D类副驾驶"]
        _tl = (profile or {}).get("tech_level") or "B类副驾驶"
        _tl_idx = next((i for i, t in enumerate(TECH_LEVELS) if _tl == t or _tl in t), 1)
        tech_level = st.selectbox("技术等级", TECH_LEVELS, index=_tl_idx, key="tech_level")
        radio_qual = st.radio("报务资格", ["无", "有"], horizontal=True, index=0 if _d("radio_qual") in ("无", "否") else 1, key="radio_qual")
        total_landings = st.number_input("总起落", min_value=0, value=int(_d("total_landings")), key="total_landings")
        total_hours = st.number_input("总经历（小时）", min_value=0.0, value=float(_d("total_hours")), format="%.1f", key="total_hours")
        type_landings = st.number_input("本机型起落", min_value=0, value=int(_d("type_landings")), key="type_landings")
        type_hours = st.number_input("本机型经历（小时）", min_value=0.0, value=float(_d("type_hours")), format="%.1f", key="type_hours")

    with col2:
        previous_aircraft = st.text_input("曾飞机型（可为空）", value=_d("previous_aircraft"), key="prev_aircraft", placeholder="如：B737")
        dg_exp = st.date_input("危险品有效期", value=datetime(2027, 8, 25).date(), key="dg_exp")
        seasonal_training = st.date_input("上次换季学习时间", value=datetime(2025, 10, 6).date(), key="seasonal_training")
        app_alert = st.radio("移动飞行APP告警", ["无", "有"], horizontal=True, index=0 if _d("app_alert") in ("无", "否") else 1, key="app_alert")
        docs_valid = st.radio("证件是否齐全", ["齐全有效", "不全"], horizontal=True, index=0, key="docs_valid")
        online_prep = st.selectbox("网上准备完成情况", ["是", "否", "连飞"], key="online_prep")
        efb_status = st.text_input("EFB电量及更新", value=_d("efb_status"), key="efb_status")

    with col3:
        studied_route = st.radio("是否学习航线手册", ["已学习", "未学习"], horizontal=True, index=0, key="studied_route")
        rnp_qual = st.radio("有无低能见/RNP APCH资格", ["有", "无"], horizontal=True, index=0, key="rnp_qual")
        last_pf_date = st.date_input("上次主飞起落日期", value=datetime.now().date(), key="last_pf_date")
        aircraft_type = st.selectbox("机型", ["A320", "A321"], key="aircraft_type")
        last_pf_time = f"{last_pf_date.strftime('%Y-%m-%d')} / {aircraft_type}"
        landing_quality = st.text_area("最近起落状态", value=_d("landing_quality"), key="landing_quality", placeholder="起落状况/质量/不足之处")

    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("从数据库加载个人资质", key="load_profile"):
            p = get_profile()
            if p:
                mapping = [
                    ("name", "name"), ("tech_level", "tech_level"), ("radio_qual", "radio_qual"),
                    ("total_landings", "total_landings"), ("total_hours", "total_hours"),
                    ("type_landings", "type_landings"), ("type_hours", "type_hours"),
                    ("previous_aircraft", "prev_aircraft"), ("app_alert", "app_alert"),
                    ("efb_status", "efb_status"), ("last_pf_time", "last_pf"),
                    ("landing_quality", "landing_quality"), ("pickup_location", "pickup"),
                ]
                for profile_key, widget_key in mapping:
                    val = p.get(profile_key)
                    if val is not None and str(val).strip() != "":
                        v = str(val).strip()
                        if profile_key == "radio_qual" and v in ("是", "否"):
                            v = "有" if v == "是" else "无"
                        if profile_key == "app_alert" and v in ("是", "否"):
                            v = "有" if v == "是" else "无"
                        st.session_state[widget_key] = v
                st.rerun()
            else:
                st.warning("数据库中暂无个人资质，请先保存。")
    with c2:
        if st.button("保存当前个人资质到数据库", key="save_profile"):
            save_profile({
                "name": co_pilot_name,
                "tech_level": tech_level,
                "radio_qual": radio_qual,
                "total_landings": total_landings,
                "total_hours": total_hours,
                "type_landings": type_landings,
                "type_hours": type_hours,
                "previous_aircraft": previous_aircraft or "无",
                "app_alert": app_alert,
                "efb_status": efb_status,
                "last_pf_time": last_pf_time,
                "landing_quality": landing_quality,
                "pickup_location": st.session_state.get("pickup", DEFAULTS["pickup_location"]),
            })
            st.success("已保存到数据库。")

# 天气与特殊天气的默认导出文案（不填写时使用）
DEFAULT_WEATHER = "起飞、航路、目的地、备降场天气"
DEFAULT_SPECIAL_WEATHER = "如低能见（云底高低于150米，能见度低于1000米）、雷雨天气、大风天气（地面风速超过30节，侧风超过15节）、严重积冰、严重颠簸"

with tab_flight:
    st.header("航班概况")
    col1, col2 = st.columns(2)

    with col1:
        # 获取已保存的航班号作为历史记录
        flights = list_flights()
        flight_numbers = [f["flight_number"] for f in flights if f["flight_number"]]
        if flight_numbers:
            flight_number = st.selectbox("航班号", options=["CZ"] + flight_numbers, key="flight_no", placeholder="CZ 后填数字，如 3835/6")
        else:
            flight_number = st.text_input("航班号", value="CZ", key="flight_no_text", placeholder="CZ 后填数字，如 3835/6")
        if st.button("从数据库匹配航班信息", key="match_flight"):
            fn = st.session_state.get("flight_no", "").strip()
            if fn:
                f = get_flight_by_number(fn)
                if f:
                    st.session_state["route"] = f.get("route", "")
                    st.session_state["dep_time"] = f.get("dep_time", "")
                    st.session_state["sign_in"] = f.get("sign_in_time", "")
                    st.rerun()
                else:
                    st.warning("未在数据库中找到该航班号对应航线/时间，请先在「数据库管理」中添加航班数据。")
            else:
                st.warning("请先填写航班号。")
        route = st.text_input("航线", key="route", placeholder="如：三亚-浦东-三亚")
        if st.button("从数据库加载航线风险与提示", key="load_route_risks"):
            r = st.session_state.get("route", "")
            loaded_risks = get_risks_for_route(r)
            loaded_notams = get_notams_for_route(r)
            if loaded_risks or loaded_notams:
                if loaded_risks:
                    st.session_state["route_risks"] = loaded_risks
                if loaded_notams:
                    st.session_state["notams"] = loaded_notams
                st.rerun()
            else:
                st.warning("未在数据库中找到该航线所含机场的风险与提示，请先在「数据库管理」中添加机场。")
        route_risks = st.text_area("航线特点及风险", key="route_risks")
        dep_time = st.text_input("起飞时间（HHMM）", key="dep_time", placeholder="如：1350")
        sign_in_time = st.text_input("签到时间（HHMM）", key="sign_in", placeholder="如：1220")
        captain = st.text_input("机长", key="captain")
        co_pilots = st.text_input("副驾驶（可多人）", key="co_pilots")
        other_crew = st.text_input("其他机组", key="other_crew", placeholder="无")
        weather_summary = st.text_area("天气状况", key="weather", placeholder="不填则导出默认：起飞、航路、目的地、备降场天气")
        special_weather = st.text_area("特殊天气", key="special_weather", placeholder="不填则导出默认说明")
        notams = st.text_area("航行通告", key="notams")

    with col2:
        special_airports = st.radio("是否涉及特殊机场", ["否", "是"], horizontal=True, index=0, key="special_airports")
        special_airport_note = st.session_state.get("special_airport_note", "")
        if special_airports == "是":
            special_airport_note = st.text_input("请填写特殊机场（如：昆明、大连）", value=special_airport_note, key="special_airport_note", placeholder="昆明、大连等")
        special_approach = st.radio("是否使用特殊飞行方法", ["否", "是"], horizontal=True, index=0, key="special_approach")
        mels_prepared = st.text_input("飞机故障保留准备", value="当天查看", key="mels")
        long_flight = st.radio("是否长航段/跨时区", ["否", "是"], horizontal=True, index=0, key="long_flight")
        other_risks = st.text_area("其他风险提示", key="other_risks", placeholder="稳定进近标准、鸟击、风切变等")
        pickup_location = st.text_input("上车地点", value=_d("pickup_location"), key="pickup")

with tab_db:
    st.header("数据库管理")
    st.subheader("航班数据")
    st.caption("添加航班号、航线、起飞时间、签到时间后，在「航班概况」中填写航班号（如 CZ3835/6）并点击「从数据库匹配航班信息」即可自动填入航线与时间。")
    with st.expander("添加 / 编辑航班", expanded=False):
        # 检查是否处于编辑模式
        if "edit_flight_id" in st.session_state:
            # 使用临时变量避免key冲突
            edit_id = st.session_state["edit_flight_id"]
            db_flight_no = st.text_input("航班号（如 CZ3835/6）", value=st.session_state.get("edit_flight_no", ""), key=f"db_flight_no_{edit_id}", placeholder="CZ3835/6")
            db_route = st.text_input("航线", value=st.session_state.get("edit_route", ""), key=f"db_route_{edit_id}", placeholder="如：三亚-浦东-三亚")
            db_dep = st.text_input("起飞时间（HHMM）", value=st.session_state.get("edit_dep", ""), key=f"db_dep_{edit_id}", placeholder="1350")
            db_sign = st.text_input("签到时间（HHMM）", value=st.session_state.get("edit_sign", ""), key=f"db_sign_{edit_id}", placeholder="1220")
            col_btn = st.columns([1, 1])
            with col_btn[0]:
                if st.button("保存修改", key=f"save_edit_flight_{edit_id}"):
                    try:
                        if db_flight_no and db_flight_no.strip():
                            add_or_update_flight(db_flight_no.strip(), db_route, db_dep, db_sign)
                            st.success("已更新航班信息。")
                            # 清除编辑状态
                            del st.session_state["edit_flight_id"]
                            del st.session_state["edit_flight_no"]
                            del st.session_state["edit_route"]
                            del st.session_state["edit_dep"]
                            del st.session_state["edit_sign"]
                            st.rerun()
                        else:
                            st.error("请填写航班号。")
                    except Exception as e:
                        st.error(f"更新失败：{str(e)}")
            with col_btn[1]:
                if st.button("取消", key=f"cancel_edit_flight_{edit_id}"):
                    del st.session_state["edit_flight_id"]
                    del st.session_state["edit_flight_no"]
                    del st.session_state["edit_route"]
                    del st.session_state["edit_dep"]
                    del st.session_state["edit_sign"]
                    st.rerun()
        else:
            db_flight_no = st.text_input("航班号（如 CZ3835/6）", value="CZ", key="db_flight_no_add", placeholder="CZ3835/6")
            db_route = st.text_input("航线", key="db_route_add", placeholder="如：三亚-浦东-三亚")
            db_dep = st.text_input("起飞时间（HHMM）", key="db_dep_add", placeholder="1350")
            db_sign = st.text_input("签到时间（HHMM）", key="db_sign_add", placeholder="1220")
            if st.button("保存航班到数据库", key="save_flight"):
                if db_flight_no and db_flight_no.strip():
                    add_or_update_flight(db_flight_no.strip(), db_route, db_dep, db_sign)
                    st.success("已保存航班。")
                    st.rerun()
                else:
                    st.error("请填写航班号。")
    st.write("已保存的航班")
    flights = list_flights()
    if not flights:
        st.info("暂无航班数据，请在上方添加。")
    else:
        for f in flights:
            with st.expander(f"航班 {f['flight_number']} — {f['route'] or '(未填航线)'}"):
                st.text(f"航线：{f['route']} | 起飞：{f['dep_time']} | 签到：{f['sign_in_time']}")
                col_edit_del = st.columns([1, 1])
                with col_edit_del[0]:
                    if st.button("编辑", key=f"edit_flight_{f['id']}"):
                        # 直接弹出编辑表单，使用全宽布局
                        st.markdown("""
                        <style>
                        .stExpander > div:nth-child(2) {
                            max-width: 100% !important;
                            width: 100% !important;
                        }
                        .stTextArea textarea {
                            width: 100% !important;
                            min-height: 150px !important;
                        }
                        .stTextInput > div > div > input {
                            width: 100% !important;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        with st.expander("编辑航班信息", expanded=False):
                            edit_flight_no = st.text_input("航班号", value=f["flight_number"], key=f"edit_flight_no_{f['id']}", placeholder="CZ3835/6")
                            edit_route = st.text_input("航线", value=f["route"], key=f"edit_route_{f['id']}", placeholder="如：三亚-浦东-三亚")
                            edit_dep = st.text_input("起飞时间（HHMM）", value=f["dep_time"], key=f"edit_dep_{f['id']}", placeholder="1350")
                            edit_sign = st.text_input("签到时间（HHMM）", value=f["sign_in_time"], key=f"edit_sign_{f['id']}", placeholder="1220")
                            
                            col_btn = st.columns([1, 1])
                            with col_btn[0]:
                                if st.button("保存修改", key=f"save_edit_flight_{f['id']}"):
                                    try:
                                        if edit_flight_no and edit_flight_no.strip():
                                            add_or_update_flight(edit_flight_no.strip(), edit_route, edit_dep, edit_sign)
                                            st.success("已更新航班信息。")
                                            st.rerun()
                                        else:
                                            st.error("请填写航班号。")
                                    except Exception as e:
                                        st.error(f"更新失败：{str(e)}")
                            with col_btn[1]:
                                if st.button("取消", key=f"cancel_edit_flight_{f['id']}"):
                                    st.rerun()
                with col_edit_del[1]:
                    if st.button("删除", key=f"del_flight_{f['id']}"):
                        delete_flight(f["id"])
                        st.rerun()

    st.subheader("机场风险与提示")
    st.caption("添加机场后，在「航班概况」中填写航线（如 三亚-浦东-三亚），点击「从数据库加载航线风险与提示」即可将对应机场的风险与通告填入「航线特点及风险」。")
    with st.expander("添加新机场", expanded=False):
        ap_name = st.text_input("机场名称（如：浦东、三亚）", key="db_airport_name_add", placeholder="用于航线匹配，如 三亚-浦东-三亚 中的 三亚、浦东")
        ap_risks = st.text_area("该机场的航线特点及风险 / 风险提示", key="db_airport_risks_add", placeholder="可多行")
        ap_notams = st.text_area("该机场的航行通告提示（可选）", key="db_airport_notams_add", placeholder="可多行")
        if st.button("保存到数据库", key="save_airport"):
            if ap_name and ap_name.strip():
                add_or_update_airport(ap_name.strip(), ap_risks, ap_notams)
                st.success(f"已保存机场「{ap_name.strip()}」。")
                st.session_state["db_airport_name_add"] = ""
                st.session_state["db_airport_risks_add"] = ""
                st.session_state["db_airport_notams_add"] = ""
                st.rerun()
            else:
                st.error("请填写机场名称。")

    st.subheader("已保存的机场")
    st.caption("直接在下方修改机场信息，改完后点击「保存修改」即可。")
    airports = list_airports()
    if not airports:
        st.info("暂无机场数据，请在上方添加。")
    else:
        for a in airports:
            with st.expander(f"机场：{a['airport_name']}", expanded=False):
                edit_name = st.text_input("机场名称", value=a["airport_name"], key=f"edit_airport_name_{a['id']}", placeholder="如：三亚、浦东")
                edit_risks = st.text_area("风险与提示", value=a["risks_tips"], key=f"edit_airport_risks_{a['id']}", height=200, placeholder="可多行")
                edit_notams = st.text_area("通告提示", value=a["notams_tips"], key=f"edit_airport_notams_{a['id']}", height=150, placeholder="可多行")
                col_save_del = st.columns([1, 1])
                with col_save_del[0]:
                    if st.button("保存修改", key=f"save_airport_{a['id']}"):
                        try:
                            if edit_name and edit_name.strip():
                                add_or_update_airport(edit_name.strip(), edit_risks, edit_notams)
                                st.success(f"已更新机场「{edit_name.strip()}」。")
                                st.rerun()
                            else:
                                st.error("请填写机场名称。")
                        except Exception as e:
                            st.error(f"更新失败：{str(e)}")
                with col_save_del[1]:
                    if st.button("删除", key=f"del_airport_{a['id']}"):
                        delete_airport(a["id"])
                        st.rerun()

# 生成文档区域
st.divider()

def generate_document():
    _special_airports_display = special_airports
    if special_airports == "是" and (special_airport_note or "").strip():
        _special_airports_display = f"是（{(special_airport_note or '').strip()}）"
    document = f"""副驾驶部分:
第一部分 个人资质
姓名：{co_pilot_name}
目前技术等级：{tech_level}
报务资格：{radio_qual}
总起落：{int(total_landings)}        总经历：{int(total_hours)}
本机型起落：{int(type_landings)}      本机型经历：{int(type_hours)}
曾飞机型：{previous_aircraft}
危险品有效期：{dg_exp}
上次参加换季学习时间：{seasonal_training}
移动飞行 APP 有无资质告警：{app_alert}
执照、体检合格证、登机牌、护照等证件是否齐全有效：{docs_valid}
网上准备完成情况：{online_prep}（是/否/连飞） 
EFB 电量及资料更新情况：{efb_status}
是否学习该航线的航线手册及相关机场细则：{studied_route}
有无低能见/RNP APCH 资格：{rnp_qual}
上次主飞起落时间及机型：{last_pf_time}
最近起落状态（起落状况/质量/不足之处）：{landing_quality}

第二部分 航班概况 
1.航班情况
-航班号：{flight_number}
-航线：{route}
-起飞时间：{dep_time}
-签到时间：{sign_in_time}
-机长：{captain}
-副驾驶：{co_pilots}
-其他机组（如有）：{other_crew}
2.天气状况（起飞、航路、目的、备降场）：
3.特殊天气，如低能见（云底高低于150米，能见度低于1000米）、雷雨天气、大风天气（地面风速超过30节，侧风超过15节）、严重积冰、严重颠簸：
4.航行通告（起飞、航路、目的地重要通告）：
5.航线特点及风险：{route_risks.replace('【', '').replace('】', '').strip()}
7.预计是否使用特殊飞行方法（盘旋进近，LDA进近，VOR/GPS/LOC/ADF等）：{special_approach}
8.是否已对飞机故障保留项目进行准备（重点关注涉及 O 项或有飞行运行限制的故障）：{mels_prepared}
9. 是否涉及飞行时间长、航段多、跨时区超过 6 小时：{long_flight}
10. 其他风险提示/注意事项：（如稳定进近标准、鸟击、风切变、近地警告处置、超速及抖杆预防和改出、地面滑行风险、单发滑行、雷雨绕飞）：{other_risks}
11.上车地点：{pickup_location}
"""
    st.session_state.generated_doc = document
    # 保存“上次主飞起落时间及机型”到数据库，下次默认显示
    if last_pf_time and str(last_pf_time).strip():
        update_last_pf_time(last_pf_time.strip())

if st.button("🚀 生成准备文档", type="primary"):
    generate_document()

if st.session_state.generated_doc:
    document = st.session_state.generated_doc
    st.text_area("准备文档输出", value=document, height=500, key="output", disabled=True)
    btn_col1, btn_col2, _ = st.columns([1, 1, 4])
    with btn_col1:
        st.info("📋 复制：在输出框中 Ctrl+A 全选后 Ctrl+C 复制")
    with btn_col2:
        st.download_button(
            label="💾 保存为TXT",
            data=document,
            file_name=f"飞行准备_{co_pilot_name or '未命名'}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            key="download_btn"
        )
