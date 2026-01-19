import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 页面配置 & 辅助函数
# -----------------------------------------------------------------------------
st.set_page_config(page_title="数据分析可视化面板 (定制排序版)", layout="wide")
st.title("📊 每周数据分析可视化面板 (定制排序版)")

# --- 定义固定排序列表 ---
IMG_TEXT_ORDER = [
    "时政军事及深度违法类",
    "影响国家安全、制度",
    "血腥暴力（暴赌毒刀具）",
    "谣言、事实错误",
    "封建迷信",
    "淫秽色情低俗",
    "过时",
    "敏感话题",
    "劣质内容",
    "硬广告、软文广告、导流广告",
    "侵权",
    "损害微软核心利益、违背MS NEWS提倡的内容价值观",
    "公司负面、竞对PR信息",
    "其他（重复、令人不适、未上线品牌等）"
]

VIDEO_ORDER = [
    "竖屏、拉伸变形",
    "脏话",
    "过时",
    "模糊",
    "不完整",
    "时长小于20秒",
    "AI生成",
    "题文&图文不符、标题错别字、读不通",
    "杂音、破音、没有声音",
    "无中文字幕的外语视频",
    "侵权",
    "广告",
    "其他合规问题（涉政、涉黄、血腥暴力等）"
]

@st.cache_data
def process_data(uploaded_files):
    """读取、合并并清洗数据"""
    dfs = []
    for file in uploaded_files:
        try:
            temp_df = pd.read_csv(file)
            dfs.append(temp_df)
        except:
            try:
                temp_df = pd.read_excel(file)
                dfs.append(temp_df)
            except Exception as e:
                st.error(f"无法读取文件 {file.name}: {e}")
    
    if not dfs:
        return pd.DataFrame()
        
    df = pd.concat(dfs, ignore_index=True)
    
    # 1. 时间处理
    df['ActionTime'] = pd.to_datetime(df['ActionTime'], errors='coerce')
    df = df.dropna(subset=['ActionTime'])
    
    # 核心：将 Date 转换为字符串，彻底避免被识别为连续时间轴
    df['Date'] = df['ActionTime'].dt.strftime('%Y-%m-%d') 
    df['Hour'] = df['ActionTime'].dt.hour
    
    # 2. 类目定义
    img_text_list = ['图文简单列表', '图文一般列表', '图文优质列表']
    video_list = ['视频高优列表', '视频一般列表']
    
    def get_category(rank_list):
        if rank_list in img_text_list: return '图文'
        elif rank_list in video_list: return '视频'
        else: return '其他'
    df['Category'] = df['RankList'].apply(get_category)
    
    # 3. 拒绝理由处理 (取第一个)
    def get_primary_reason(reason):
        if pd.isna(reason) or str(reason).strip() == "": return "未知"
        # 统一分隔符
        r = str(reason).replace('，', ',').replace(';', ',').split(',')[0].strip()
        return r
    df['PrimaryReason'] = df['Reason'].apply(get_primary_reason)
    
    return df

# -----------------------------------------------------------------------------
# 2. 侧边栏 & 数据加载
# -----------------------------------------------------------------------------
st.sidebar.header("📂 数据上传")
uploaded_files = st.sidebar.file_uploader(
    "上传表格文件 (支持多选，自动合并)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

if uploaded_files:
    df = process_data(uploaded_files)
    
    if df.empty:
        st.warning("⚠️ 未检测到有效数据")
    else:
        # 全局筛选
        all_dates = sorted(df['Date'].unique())
        st.sidebar.success(f"✅ 已合并 {len(uploaded_files)} 个文件")
        st.sidebar.info(f"📅 数据包含日期:\n{all_dates}")
        
        # 为了筛选器方便，这里临时转回 datetime 对象来获取最大最小值，筛选后再转回字符串对比
        dates_dt = pd.to_datetime(all_dates)
        min_date, max_date = dates_dt.min().date(), dates_dt.max().date()
        
        selected_dates = st.sidebar.date_input("选择日期范围", [min_date, max_date], min_value=min_date, max_value=max_date)
        
        if len(selected_dates) == 2:
            # 字符串日期对比: 将筛选器的 date 对象转为字符串
            start_s = selected_dates[0].strftime('%Y-%m-%d')
            end_s = selected_dates[1].strftime('%Y-%m-%d')
            mask = (df['Date'] >= start_s) & (df['Date'] <= end_s)
            df_filtered = df.loc[mask]
        else:
            df_filtered = df

        # 配色
        pastel_colors = [[0.0, '#E8F5E9'], [0.2, '#C8E6C9'], [0.5, '#FFF9C4'], [0.8, '#FFCCBC'], [1.0, '#EF9A9A']]

        tab1, tab2, tab3, tab4 = st.tabs(["1. 各类目下线理由统计", "2. Provider 拒绝排行", "3. 视频每日详情", "4. Requester 效率热力图"])

        # --- Tab 1: 各类目下线理由统计 (双表格逻辑) ---
        with tab1:
            st.header("各类目下线理由及审核情况统计")
            
            categories = ['图文', '视频']
            # 定义该类目的固定排序列表
            order_map = {
                '图文': IMG_TEXT_ORDER,
                '视频': VIDEO_ORDER
            }
            
            for cat in categories:
                st.subheader(f"📂 {cat}类目")
                cat_df = df_filtered[df_filtered['Category'] == cat]
                
                if cat_df.empty:
                    st.info("无数据")
                    continue
                
                # 总体指标
                total_audit = len(cat_df)
                status_counts = cat_df['Action'].value_counts()
                rejected_count = status_counts.get('Rejected', 0)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("审核总数", total_audit)
                c2.metric("上线数量", status_counts.get('Approved', 0))
                c3.metric("下线数量", rejected_count)
                
                if rejected_count > 0:
                    rej_df = cat_df[cat_df['Action'] == 'Rejected']
                    # 原始统计
                    raw_stats = rej_df['PrimaryReason'].value_counts().reset_index()
                    raw_stats.columns = ['下线理由', '下线数量']
                    
                    # --- 表格 1: 按数量降序 (保持原样) ---
                    df_sorted_count = raw_stats.copy()
                    df_sorted_count['下线占比'] = (df_sorted_count['下线数量'] / rejected_count * 100).apply(lambda x: f"{x:.2f}%")
                    df_sorted_count['审核总数占比'] = (df_sorted_count['下线数量'] / total_audit * 100).apply(lambda x: f"{x:.2f}%")
                    
                    # --- 表格 2: 按固定顺序排列 ---
                    target_order = order_map.get(cat, [])
                    
                    # 创建一个包含所有固定理由的 DataFrame (确保即使数量为0也显示? 或者只排序存在的? 通常固定表单需要显示所有项，这里我们为了严谨，先显示所有项)
                    # 也可以选择：只对存在的数据进行排序。根据您的需求“按照下方的类目顺序排列”，通常意味着类似检查清单的顺序。
                    
                    # 策略：将统计数据 merge 到固定列表上
                    order_df = pd.DataFrame(target_order, columns=['下线理由'])
                    # 左连接：保留固定列表的所有项
                    merged_df = pd.merge(order_df, raw_stats, on='下线理由', how='left')
                    merged_df['下线数量'] = merged_df['下线数量'].fillna(0).astype(int)
                    
                    # 处理不在固定列表中的“其他”项 (防止漏掉数据)
                    existing_reasons = set(merged_df['下线理由'].tolist())
                    all_reasons = set(raw_stats['下线理由'].tolist())
                    missing_reasons = list(all_reasons - existing_reasons)
                    
                    if missing_reasons:
                        missing_df = raw_stats[raw_stats['下线理由'].isin(missing_reasons)]
                        merged_df = pd.concat([merged_df, missing_df], ignore_index=True)
                    
                    # 计算百分比
                    merged_df['下线占比'] = (merged_df['下线数量'] / rejected_count * 100).apply(lambda x: f"{x:.2f}%")
                    merged_df['审核总数占比'] = (merged_df['下线数量'] / total_audit * 100).apply(lambda x: f"{x:.2f}%")
                    
                    # 展示
                    st.write(f"**{cat} - 表1: 按数量从高到低排列**")
                    st.dataframe(df_sorted_count, use_container_width=True)
                    
                    st.write(f"**{cat} - 表2: 按指定固定顺序排列**")
                    st.dataframe(merged_df, use_container_width=True)
                    
                st.markdown("---")

        # --- Tab 2: Provider 拒绝排行 ---
        with tab2:
            st.header("Provider 拒绝排行及占比分析")
            for cat in categories:
                st.subheader(f"🏢 {cat} - Provider 分析")
                cat_df = df_filtered[df_filtered['Category'] == cat]
                if cat_df.empty:
                    st.info("无数据"); continue

                cat_total_audit = len(cat_df)
                cat_total_rejected = len(cat_df[cat_df['Action'] == 'Rejected'])
                
                rej_counts = cat_df[cat_df['Action'] == 'Rejected'].groupby('ProviderName').size().reset_index(name='Rejected Count')
                total_counts = cat_df.groupby('ProviderName').size().reset_index(name='Provider Total Audit')
                top_reasons = cat_df[cat_df['Action'] == 'Rejected'].groupby('ProviderName')['PrimaryReason'].apply(lambda x: x.mode()[0] if len(x)>0 else "N/A").reset_index(name='Top Reason')
                
                if not rej_counts.empty:
                    merged = pd.merge(rej_counts, total_counts, on='ProviderName', how='left')
                    merged = pd.merge(merged, top_reasons, on='ProviderName', how='left')
                    
                    merged['Provider自身下线率'] = (merged['Rejected Count'] / merged['Provider Total Audit'] * 100).apply(lambda x: f"{x:.2f}%")
                    merged['占总下线量占比'] = (merged['Rejected Count'] / cat_total_rejected * 100).apply(lambda x: f"{x:.2f}%")
                    merged['占总审核量占比'] = (merged['Rejected Count'] / cat_total_audit * 100).apply(lambda x: f"{x:.2f}%")
                    
                    cols = ['ProviderName', 'Rejected Count', 'Top Reason', 'Provider自身下线率', '占总下线量占比', '占总审核量占比', 'Provider Total Audit']
                    st.dataframe(merged.sort_values('Rejected Count', ascending=False)[cols], use_container_width=True)
                else:
                    st.info("无 Rejected 数据")

        # --- Tab 3: 视频每日详情 ---
        with tab3:
            st.header("视频 Provider 每日详情")
            video_df = df_filtered[df_filtered['Category'] == '视频']
            if not video_df.empty:
                for prov in video_df['ProviderName'].unique():
                    st.subheader(f"📺 {prov}")
                    p_data = video_df[video_df['ProviderName'] == prov]
                    daily = p_data.groupby(['Date', 'Action']).size().unstack(fill_value=0).reset_index()
                    for c in ['Approved', 'Rejected']: 
                        if c not in daily.columns: daily[c] = 0
                    
                    daily['审核总数'] = daily['Approved'] + daily['Rejected']
                    daily = daily.rename(columns={'Approved': '上线总数', 'Rejected': '下线总数'})
                    daily['上线占比'] = daily.apply(lambda x: f"{(x['上线总数']/x['审核总数']*100):.2f}%" if x['审核总数']>0 else "0.00%", axis=1)
                    daily = daily.sort_values('Date')
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=daily['Date'], y=daily['上线总数'], name='上线', marker_color='#A5D6A7', text=daily['上线总数'], textposition='outside'))
                    fig.add_trace(go.Bar(x=daily['Date'], y=daily['下线总数'], name='下线', marker_color='#EF9A9A', text=daily['下线总数'], textposition='outside'))
                    fig.update_layout(title=f'{prov} 每日趋势', barmode='group', height=350)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(daily, use_container_width=True)
                    st.markdown("---")
            else:
                st.info("无视频数据")

        # --- Tab 4: Requester 效率热力图 (日期轴强制为字符串分类) ---
        with tab4:
            st.header("Requester 每日分时段效率")
            st.markdown("说明：纵轴日期已强制为分类显示，每行代表一天的完整数据 (0点, 5-23点)。")
            
            target_hours = [0] + list(range(5, 24))
            
            # 使用字符串日期列表
            if not df_filtered.empty:
                # 获取筛选范围内所有的日期字符串
                all_dates_in_range = sorted(df_filtered['Date'].unique())
            else:
                all_dates_in_range = []

            requesters = df_filtered['Requester'].unique()
            cols = st.columns(2)
            
            for i, req in enumerate(requesters):
                col = cols[i % 2]
                with col:
                    st.subheader(f"👤 {req}")
                    req_data = df_filtered[df_filtered['Requester'] == req]
                    
                    if len(all_dates_in_range) > 0:
                        # A. 构建网格 (Date 已经是字符串)
                        idx = pd.MultiIndex.from_product([all_dates_in_range, target_hours], names=['Date', 'Hour'])
                        grid_df = pd.DataFrame(index=idx).reset_index()
                        
                        # B. 统计
                        valid_req_data = req_data[req_data['Hour'].isin(target_hours)]
                        # 注意：req_data['Date'] 已经是字符串
                        actual_counts = valid_req_data.groupby(['Date', 'Hour']).size().reset_index(name='Count')
                        
                        # C. 合并
                        merged = pd.merge(grid_df, actual_counts, on=['Date', 'Hour'], how='left')
                        merged['Count'] = merged['Count'].fillna(0).astype(int)
                        
                        # D. 绘图
                        fig = px.density_heatmap(
                            merged, 
                            x='Hour', 
                            y='Date', # 这里直接用字符串列
                            z='Count', 
                            text_auto=True,
                            color_continuous_scale=pastel_colors,
                            title=f'{req} 效率分布'
                        )
                        
                        fig.update_layout(
                            xaxis_title="小时 (0点, 5-23点)",
                            yaxis_title="日期",
                            coloraxis_showscale=False,
                            # 强制 X 轴和 Y 轴都为分类轴
                            xaxis=dict(type='category', categoryorder='array', categoryarray=target_hours),
                            yaxis=dict(type='category', categoryorder='category ascending')
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write("无数据")
                    st.markdown("---")