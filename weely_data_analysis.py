import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go

# =====================================================================
# 全局页面配置
# =====================================================================
st.set_page_config(page_title="审核数据综合看板", layout="wide", page_icon="📈")

# =====================================================================
# 共用常量定义
# =====================================================================
DEFAULT_NAME_LIST = [
    'v-qingqinghe@microsoft.com', 'v-yangyang5@microsoft.com', 'v-qiangwei@microsoft.com',
    'v-cwen@microsoft.com', 'v-yuehan@microsoft.com', 'v-xiyuan1@microsoft.com',
    'v-xuelyang@microsoft.com', 'v-tengpan@microsoft.com', 'v-qinjiang@microsoft.com',
    'v-yancche@microsoft.com', 'v-chenqia@microsoft.com', 'v-yumeiliang@microsoft.com',
    'v-haoyu4@microsoft.com', 'v-xinyuma@microsoft.com', 'v-dandanli@microsoft.com',
    'v-yuanjunli@microsoft.com', 'v-yuqincheng@microsoft.com', 'v-wangjua@microsoft.com',
    'v-qingkzhang@microsoft.com', 'v-minshi1@microsoft.com', 'v-hengma@microsoft.com',
    'v-yingxli@microsoft.com', 'v-peilirao@microsoft.com', 'v-jiangqia@microsoft.com',
    'v-chaozhao@microsoft.com', 'v-huanyuluo@microsoft.com',
    'v-liyuchen@microsoft.com'
]

IMG_TEXT_ORDER = [
    "时政军事及深度违法类", "影响国家安全、制度", "血腥暴力（暴赌毒刀具）", "谣言、事实错误",
    "封建迷信", "淫秽色情低俗", "过时", "敏感话题", "劣质内容", "硬广告、软文广告、导流广告",
    "侵权", "损害微软核心利益、违背MS NEWS提倡的内容价值观", "公司负面、竞对PR信息",
    "其他（重复、令人不适、未上线品牌等）"
]

VIDEO_ORDER = [
    "竖屏、拉伸变形", "脏话", "过时", "模糊", "不完整", "时长小于20秒", "AI生成",
    "题文&图文不符、标题错别字、读不通", "杂音、破音、没有声音", "无中文字幕的外语视频",
    "侵权", "广告", "其他合规问题（涉政、涉黄、血腥暴力等）"
]

# =====================================================================
# 共用数据读取函数 (带有缓存以加速切换)
# =====================================================================
@st.cache_data
def load_and_concat_files(uploaded_files):
    dfs = []
    for file in uploaded_files:
        try:
            if file.name.endswith('.csv'):
                try:
                    temp_df = pd.read_csv(file, encoding='utf-8')
                except UnicodeDecodeError:
                    file.seek(0)
                    temp_df = pd.read_csv(file, encoding='gbk')
            else:
                temp_df = pd.read_excel(file)
            # 清理列名前后空格防止KeyError
            temp_df.columns = temp_df.columns.str.strip() 
            dfs.append(temp_df)
        except Exception as e:
            st.sidebar.error(f"无法读取文件 {file.name}: {e}")
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


# =====================================================================
# 侧边栏结构
# =====================================================================
st.sidebar.title("🧭 功能导航")
app_mode = st.sidebar.radio(
    "选择你要查看的面板类型:", 
    ["📈 每日明细报表 (排班宽表)", "📊 每周综合分析 (通过率/热力图)"]
)

st.sidebar.markdown("---")
st.sidebar.header("📂 数据上传 (全局共用)")
uploaded_files = st.sidebar.file_uploader(
    "支持拖入多个 CSV/Excel 文件 (自动合并)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

# =====================================================================
# 主体逻辑
# =====================================================================
if uploaded_files:
    # 统一读取数据
    with st.spinner('正在处理数据...'):
        raw_df = load_and_concat_files(uploaded_files)
        
    if raw_df.empty:
        st.warning("⚠️ 未能从文件中解析出有效数据。")
        st.stop()
        
    st.sidebar.success(f"✅ 成功加载 {len(uploaded_files)} 个文件数据。")

    # 检查两个面板必需的核心列
    if 'ActionTime' not in raw_df.columns or 'RankList' not in raw_df.columns:
        st.error(f"❌ 读取失败：找不到 'ActionTime' 或 'RankList' 列。当前表格列名有：{list(raw_df.columns)}")
        st.stop()
        
    # 通用的时间清洗（去除无法转换的空时间）
    raw_df['ActionTime'] = pd.to_datetime(raw_df['ActionTime'], errors='coerce')
    raw_df = raw_df.dropna(subset=['ActionTime'])

    # -------------------------------------------------------------------
    # 面板 1：每日明细排班看板 (沿用之前的规则)
    # -------------------------------------------------------------------
    if app_mode == "📈 每日明细报表 (排班宽表)":
        st.title("📈 每日审核数量明细看板 (1点-次日1点)")
        st.info("💡 提示：时间范围规则为每天的 01:00:00 至次日 01:00:00。表格包含所有指定成员，可向右滑动查看所有日期。")
        
        df1 = raw_df.copy()
        
        # 偏移时间逻辑：减掉一小时
        df1['AdjustedTime'] = df1['ActionTime'] - pd.Timedelta(hours=1)
        df1['Date'] = df1['AdjustedTime'].dt.date
        
        # 分类逻辑
        def categorize_ranklist1(x):
            if x == '图文简单列表': return '简单'
            elif x in ['图文优质列表', '图文一般列表']: return '一般+优质'
            elif x in ['视频一般列表', '视频高优列表']: return 'video'
            else: return '其他'
        df1['Category'] = df1['RankList'].apply(categorize_ranklist1)
        
        dates = sorted(df1['Date'].dropna().unique())
        all_stats_list = []
        
        for current_date in dates:
            df_date = df1[df1['Date'] == current_date]
            if not df_date.empty and 'Requester' in df1.columns:
                stats = df_date.groupby(['Requester', 'Category']).size().unstack(fill_value=0)
                
                # 补齐缺少的类别
                for col in ['简单', '一般+优质', 'video']:
                    if col not in stats.columns: stats[col] = 0
                stats = stats[['简单', '一般+优质', 'video']]
                
                # 使用预设名单重新排序对齐
                stats_reindexed = stats.reindex(DEFAULT_NAME_LIST).fillna(0).astype(int)
                stats_reindexed.loc['【当日总计】'] = stats_reindexed.sum(axis=0)
                
                # 设定多级表头 (日期横排)
                date_str = current_date.strftime("%Y-%m-%d")
                stats_reindexed.columns = pd.MultiIndex.from_product([[date_str], stats_reindexed.columns])
                all_stats_list.append(stats_reindexed)
                
        if all_stats_list:
            final_combined_df = pd.concat(all_stats_list, axis=1)
            st.dataframe(final_combined_df, use_container_width=True, height=750)
            
            csv = final_combined_df.to_csv().encode('utf-8-sig')
            st.download_button(
                label="📥 一键下载完整多日合并统计表 (CSV)",
                data=csv,
                file_name=f"审核明细多日合并报表_{dates[0]}_至_{dates[-1]}.csv",
                mime='text/csv'
            )
        else:
            st.warning("所选文件内未能解析出可用的报表数据。")

    # -------------------------------------------------------------------
    # 面板 2：每周数据分析看板 (沿用上传文件的逻辑)
    # -------------------------------------------------------------------
    elif app_mode == "📊 每周综合分析 (通过率/热力图)":
        st.title("📊 每周数据综合可视化面板 (定制排序版)")
        df2 = raw_df.copy()
        
        # 日期获取（不再做 1 小时偏移，沿用分析面板原逻辑）
        df2['Date'] = df2['ActionTime'].dt.strftime('%Y-%m-%d')
        df2['Hour'] = df2['ActionTime'].dt.hour
        
        # 大类目定义
        img_text_list = ['图文简单列表', '图文一般列表', '图文优质列表']
        video_list = ['视频高优列表', '视频一般列表']
        def categorize_ranklist2(rank_list):
            if rank_list in img_text_list: return '图文'
            elif rank_list in video_list: return '视频'
            else: return '其他'
        df2['Category'] = df2['RankList'].apply(categorize_ranklist2)
        
        # 提取第一拒绝理由
        def get_primary_reason(reason):
            if pd.isna(reason) or str(reason).strip() == "": return "未知"
            r = str(reason).replace('，', ',').replace(';', ',').split(',')[0].strip()
            return r
            
        if 'Reason' in df2.columns:
            df2['PrimaryReason'] = df2['Reason'].apply(get_primary_reason)
        else:
            df2['PrimaryReason'] = "未知"
            
        # 侧边栏日期筛选（仅对分析面板生效）
        all_dates = sorted(df2['Date'].unique())
        dates_dt = pd.to_datetime(all_dates)
        
        if len(dates_dt) > 0:
            min_date, max_date = dates_dt.min().date(), dates_dt.max().date()
            selected_dates = st.sidebar.date_input("📅 过滤图表数据日期", [min_date, max_date], min_value=min_date, max_value=max_date)
            
            if len(selected_dates) == 2:
                start_s = selected_dates[0].strftime('%Y-%m-%d')
                end_s = selected_dates[1].strftime('%Y-%m-%d')
                mask = (df2['Date'] >= start_s) & (df2['Date'] <= end_s)
                df_filtered = df2.loc[mask]
            else:
                df_filtered = df2
        else:
            df_filtered = df2
            
        pastel_colors = [[0.0, '#E8F5E9'], [0.2, '#C8E6C9'], [0.5, '#FFF9C4'], [0.8, '#FFCCBC'], [1.0, '#EF9A9A']]
        
        tab1, tab2, tab3, tab4 = st.tabs(["1. 各类目下线理由统计", "2. Provider 拒绝排行", "3. 视频每日详情", "4. Requester 效率热力图"])

        # Tab 1: 各类目下线理由统计
        with tab1:
            st.header("各类目下线理由及审核情况统计")
            order_map = {'图文': IMG_TEXT_ORDER, '视频': VIDEO_ORDER}
            for cat in ['图文', '视频']:
                st.subheader(f"📂 {cat}类目")
                cat_df = df_filtered[df_filtered['Category'] == cat]
                
                if cat_df.empty:
                    st.info(f"{cat} 类目无数据"); continue
                
                total_audit = len(cat_df)
                status_counts = cat_df['Action'].value_counts() if 'Action' in cat_df.columns else pd.Series()
                rejected_count = status_counts.get('Rejected', 0)
                approved_count = status_counts.get('Approved', 0)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("审核总数", total_audit)
                c2.metric("上线数量", approved_count)
                c3.metric("下线数量", rejected_count)
                
                if rejected_count > 0:
                    rej_df = cat_df[cat_df['Action'] == 'Rejected']
                    raw_stats = rej_df['PrimaryReason'].value_counts().reset_index()
                    raw_stats.columns = ['下线理由', '下线数量']
                    
                    df_sorted_count = raw_stats.copy()
                    df_sorted_count['下线占比'] = (df_sorted_count['下线数量'] / rejected_count * 100).apply(lambda x: f"{x:.2f}%")
                    df_sorted_count['审核总数占比'] = (df_sorted_count['下线数量'] / total_audit * 100).apply(lambda x: f"{x:.2f}%")
                    
                    target_order = order_map.get(cat, [])
                    order_df = pd.DataFrame(target_order, columns=['下线理由'])
                    merged_df = pd.merge(order_df, raw_stats, on='下线理由', how='left')
                    merged_df['下线数量'] = merged_df['下线数量'].fillna(0).astype(int)
                    
                    existing_reasons = set(merged_df['下线理由'].tolist())
                    all_reasons = set(raw_stats['下线理由'].tolist())
                    missing_reasons = list(all_reasons - existing_reasons)
                    
                    if missing_reasons:
                        missing_df = raw_stats[raw_stats['下线理由'].isin(missing_reasons)]
                        merged_df = pd.concat([merged_df, missing_df], ignore_index=True)
                        
                    merged_df['下线占比'] = (merged_df['下线数量'] / rejected_count * 100).apply(lambda x: f"{x:.2f}%")
                    merged_df['审核总数占比'] = (merged_df['下线数量'] / total_audit * 100).apply(lambda x: f"{x:.2f}%")
                    
                    colA, colB = st.columns(2)
                    with colA:
                        st.write(f"**{cat} - 表1: 按数量从高到低排列**")
                        st.dataframe(df_sorted_count, use_container_width=True)
                    with colB:
                        st.write(f"**{cat} - 表2: 按指定固定顺序排列**")
                        st.dataframe(merged_df, use_container_width=True)
                st.markdown("---")

        # Tab 2: Provider 排行
        with tab2:
            st.header("Provider 拒绝排行及占比分析")
            if 'ProviderName' not in df_filtered.columns:
                st.warning("数据中缺少 'ProviderName' 列。")
            else:
                for cat in ['图文', '视频']:
                    st.subheader(f"🏢 {cat} - Provider 分析")
                    cat_df = df_filtered[df_filtered['Category'] == cat]
                    
                    if cat_df.empty:
                        st.info(f"{cat} 类目无数据"); continue
                        
                    cat_total_audit = len(cat_df)
                    cat_total_rejected = len(cat_df[cat_df['Action'] == 'Rejected']) if 'Action' in cat_df.columns else 0
                    
                    if cat_total_rejected > 0:
                        rej_counts = cat_df[cat_df['Action'] == 'Rejected'].groupby('ProviderName').size().reset_index(name='Rejected Count')
                        total_counts = cat_df.groupby('ProviderName').size().reset_index(name='Provider Total Audit')
                        top_reasons = cat_df[cat_df['Action'] == 'Rejected'].groupby('ProviderName')['PrimaryReason'].apply(lambda x: x.mode()[0] if len(x)>0 else "N/A").reset_index(name='Top Reason')
                        
                        merged = pd.merge(rej_counts, total_counts, on='ProviderName', how='left')
                        merged = pd.merge(merged, top_reasons, on='ProviderName', how='left')
                        
                        merged['Provider自身下线率'] = (merged['Rejected Count'] / merged['Provider Total Audit'] * 100).apply(lambda x: f"{x:.2f}%")
                        merged['占总下线量占比'] = (merged['Rejected Count'] / cat_total_rejected * 100).apply(lambda x: f"{x:.2f}%")
                        merged['占总审核量占比'] = (merged['Rejected Count'] / cat_total_audit * 100).apply(lambda x: f"{x:.2f}%")
                        
                        cols = ['ProviderName', 'Rejected Count', 'Top Reason', 'Provider自身下线率', '占总下线量占比', '占总审核量占比', 'Provider Total Audit']
                        st.dataframe(merged.sort_values('Rejected Count', ascending=False)[cols], use_container_width=True)
                    else:
                        st.info("无 Rejected 数据")

        # Tab 3: 视频每日详情
        with tab3:
            st.header("视频 Provider 每日详情")
            video_df = df_filtered[df_filtered['Category'] == '视频']
            if 'ProviderName' in video_df.columns and not video_df.empty:
                for prov in video_df['ProviderName'].dropna().unique():
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
                st.info("无视频数据或缺少Provider列")

        # Tab 4: 热力图
        with tab4:
            st.header("Requester 每日分时段效率")
            st.markdown("说明：纵轴日期已强制为分类显示，每行代表一天的完整数据 (0点, 5-23点)。")
            target_hours = [0] + list(range(5, 24))
            
            all_dates_in_range = sorted(df_filtered['Date'].unique()) if not df_filtered.empty else []
            if 'Requester' in df_filtered.columns:
                requesters = df_filtered['Requester'].dropna().unique()
                cols = st.columns(2)
                for i, req in enumerate(requesters):
                    col = cols[i % 2]
                    with col:
                        st.subheader(f"👤 {req}")
                        req_data = df_filtered[df_filtered['Requester'] == req]
                        if len(all_dates_in_range) > 0:
                            idx = pd.MultiIndex.from_product([all_dates_in_range, target_hours], names=['Date', 'Hour'])
                            grid_df = pd.DataFrame(index=idx).reset_index()
                            valid_req_data = req_data[req_data['Hour'].isin(target_hours)]
                            actual_counts = valid_req_data.groupby(['Date', 'Hour']).size().reset_index(name='Count')
                            
                            merged = pd.merge(grid_df, actual_counts, on=['Date', 'Hour'], how='left')
                            merged['Count'] = merged['Count'].fillna(0).astype(int)
                            
                            fig = px.density_heatmap(
                                merged, x='Hour', y='Date', z='Count', text_auto=True,
                                color_continuous_scale=pastel_colors, title=f'{req} 效率分布'
                            )
                            fig.update_layout(
                                xaxis_title="小时 (0点, 5-23点)", yaxis_title="日期",
                                coloraxis_showscale=False,
                                xaxis=dict(type='category', categoryorder='array', categoryarray=target_hours),
                                yaxis=dict(type='category', categoryorder='category ascending')
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.write("无数据")
                        st.markdown("---")
            else:
                st.info("数据中缺少 'Requester' 列。")
else:
    st.info("👈 请在左侧边栏上传数据文件以开启分析之旅。")
