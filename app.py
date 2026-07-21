import re
import pandas as pd
import streamlit as st
import plotly.express as px

# ---------------------------
# 데이터 로드 함수
# ---------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(
        "202606_202606_yeonryeongbyeolinguhyeonhwang_weolgan_gangsanim.csv",
        encoding="cp949"
    )
    return df

# 행정구역 문자열에서 코드(괄호 안 숫자)만 추출
def extract_code(region_str: str) -> str:
    m = re.search(r"\((\d+\.?\d*e\+\d+|\d+)\)", str(region_str))
    return m.group(1) if m else ""

# 괄호 앞의 행정구역 이름만 추출
def extract_name(region_str: str) -> str:
    return re.sub(r"\(.*\)", "", str(region_str)).strip()

# ---------------------------
# 메인 앱
# ---------------------------
def main():
    st.set_page_config(
        page_title="연령별 인구 구조 뷰어",
        layout="wide"
    )

    st.title("연령별 인구 구조 웹앱")
    st.write("2026년 6월 기준 주민등록 연령별 인구현황 데이터를 이용해, 선택한 지역의 인구 구조를 꺾은선 그래프로 보여줍니다.")

    # 데이터 로드
    df = load_data()

    # 행정구역 이름/코드 분리
    df["행정구역_코드"] = df["행정구역"].apply(extract_code)
    df["행정구역_이름"] = df["행정구역"].apply(extract_name)

    # 계/남/여별 연령 컬럼 식별
    all_cols = df.columns.tolist()
    cols_total = [c for c in all_cols if c.startswith("2026년06월_계_") and "세" in c]
    cols_male = [c for c in all_cols if c.startswith("2026년06월_남_") and "세" in c]
    cols_female = [c for c in all_cols if c.startswith("2026년06월_여_") and "세" in c]

    # 연령값(숫자만) 추출해서 x축용으로 사용
    def age_from_col(col):
        m = re.search(r"_(\d+세)|_100세 이상", col)
        if m:
            s = m.group(1)
            if "100세 이상" in col:
                return 100
            else:
                return int(s.replace("세", ""))
        return None

    ages = [age_from_col(c) for c in cols_total]
    # NaN 제거
    age_cols_total = [(age, col) for age, col in zip(ages, cols_total) if age is not None]
    age_cols_total = sorted(age_cols_total, key=lambda x: x[0])

    # 남/여도 같은 순서로 정렬
    ages_m = [age_from_col(c) for c in cols_male]
    age_cols_male = [(age, col) for age, col in zip(ages_m, cols_male) if age is not None]
    age_cols_male = sorted(age_cols_male, key=lambda x: x[0])

    ages_f = [age_from_col(c) for c in cols_female]
    age_cols_female = [(age, col) for age, col in zip(ages_f, cols_female) if age is not None]
    age_cols_female = sorted(age_cols_female, key=lambda x: x[0])

    # ---------------------------
    # 사이드바: 지역 선택 & 검색
    # ---------------------------
    st.sidebar.header("지역 선택")

    # 기본 선택 리스트: 시도 + 시군구 수준까지 보여주기 (필요시 변경 가능)
    unique_regions = sorted(df["행정구역_이름"].unique().tolist())

    default_region = st.sidebar.selectbox(
        "리스트에서 지역 선택",
        options=unique_regions,
        index=unique_regions.index("서울특별시 종로구") if "서울특별시 종로구" in unique_regions else 0
    )

    manual_input = st.sidebar.text_input(
        "직접 입력 (예: 서울특별시 종로구 청운효자동)",
        value=""
    )

    # 최종 지역 이름 결정
    region_name = manual_input.strip() if manual_input.strip() else default_region

    # 선택된 지역에 해당하는 행들 필터링
    # 같은 이름을 여러 코드가 가질 수도 있어 가장 상위 하나만 사용
    region_rows = df[df["행정구역_이름"] == region_name]

    if region_rows.empty:
        st.warning(f"'{region_name}'에 해당하는 데이터를 찾을 수 없습니다. 정확한 행정구역 이름인지 확인해주세요.")
        st.stop()

    # 일단 첫 번째 행을 사용 (같은 이름의 여러 행이 있을 경우 코드로 더 정교하게 선택 가능)
    region_row = region_rows.iloc[0]

    # ---------------------------
    # 숫자 변환 (콤마 제거)
    # ---------------------------
    def to_numeric_series(series):
        return pd.to_numeric(series.astype(str).str.replace(",", ""), errors="coerce")

    y_total = to_numeric_series(region_row[[c for _, c in age_cols_total]])
    y_male = to_numeric_series(region_row[[c for _, c in age_cols_male]])
    y_female = to_numeric_series(region_row[[c for _, c in age_cols_female]])

    x_age = [age for age, _ in age_cols_total]

    # ---------------------------
    # 플롯리 그래프 생성
    # ---------------------------
    plot_df = pd.DataFrame({
        "연령": x_age,
        "계": y_total.values,
        "남": y_male.values,
        "여": y_female.values
    })

    fig = px.line(
        plot_df,
        x="연령",
        y=["계", "남", "여"],
        title=f"{region_name} 연령별 인구 구조 (2026년 6월)",
        labels={"value": "인구수", "variable": "성별"},
    )

    fig.update_layout(
        xaxis_title="연령 (세)",
        yaxis_title="인구수",
        legend_title="성별",
        hovermode="x unified",
        template="plotly_white",
    )

    # ---------------------------
    # 화면 표시
    # ---------------------------
    st.subheader(f"선택된 지역: {region_name}")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("원시 데이터 행 보기"):
        st.write(region_row)

    st.caption("데이터: 2026년 6월 주민등록 연령별 인구현황 (행정구역별, 계/남/여)")

if __name__ == "__main__":
    main()
