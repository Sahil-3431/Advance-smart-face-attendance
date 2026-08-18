import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# =====================================================
# LOAD ATTENDANCE DATAFRAME
# =====================================================

def attendance_dataframe(rows):
    columns = [
        "person_id",
        "name",
        "date",
        "time",
        "status"
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows,columns=columns)
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )
    df["time"] = pd.to_datetime(
        df["time"],
        format="%H:%M:%S",
        errors="coerce"
    ).dt.time
    return df

# =====================================================
# TODAY
# =====================================================

def get_today():
    return datetime.now(IST).date()

# =====================================================
# KPI
# =====================================================

def calculate_kpis(people_df,attendance_df):
    total_people = len(people_df)
    today = pd.Timestamp(get_today())
    if attendance_df.empty:
        today_df = pd.DataFrame()
    else:
        today_df = attendance_df[attendance_df["date"] == today]
    today_present = (
        today_df["person_id"]
        .nunique()
        if not today_df.empty
        else 0
    )
    today_absent = max(total_people - today_present,0)
    attendance_rate = (
        (today_present / total_people) * 100
        if total_people > 0
        else 0
    )
    total_records = len(attendance_df)
    return {
        "total_people": total_people,
        "today_present": today_present,
        "today_absent": today_absent,
        "attendance_rate": attendance_rate,
        "total_records": total_records
    }

# =====================================================
# DAILY TREND
# =====================================================

def daily_attendance_trend(attendance_df,start_date=None,end_date=None):
    if attendance_df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "present"
            ]
        )
    df = attendance_df.copy()
    if start_date is not None:
        df = df[df["date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        df = df[df["date"] <= pd.Timestamp(end_date)]
    if df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "present"
            ]
        )
    trend = (
        df.groupby("date")
        ["person_id"]
        .nunique()
        .reset_index(
            name="present"
        )
    )
    return trend.sort_values("date")

# =====================================================
# DEPARTMENT ANALYSIS
# =====================================================

def department_attendance(people_df,attendance_df):
    if people_df.empty:
        return pd.DataFrame()
    people = people_df.copy()
    people = people[
        [
            "person_id",
            "name",
            "department"
        ]
    ]
    people["department"] = (
        people["department"]
        .fillna("Not Assigned")
        .replace("", "Not Assigned")
    )
    if attendance_df.empty:
        people["present_days"] = 0
    else:
        present_days = (
            attendance_df
            .groupby("person_id")
            .size()
            .reset_index(
                name="present_days"
            )
        )
        people = people.merge(
            present_days,
            on="person_id",
            how="left"
        )
        people["present_days"] = (
            people["present_days"]
            .fillna(0)
        )
    result = (
        people
        .groupby("department")
        .agg(
            employees=(
                "person_id",
                "nunique"
            ),
            attendance_records=(
                "present_days",
                "sum"
            )
        )
        .reset_index()
    )
    return result.sort_values(
        "attendance_records",
        ascending=False
    )

# =====================================================
# PERSON PERFORMANCE
# =====================================================

def person_performance(people_df,attendance_df):
    if people_df.empty:
        return pd.DataFrame()
    people = people_df[
        [
            "person_id",
            "name",
            "department"
        ]
    ].copy()
    if attendance_df.empty:
        people["attendance_days"] = 0
    else:
        performance = (
            attendance_df
            .groupby("person_id")
            ["date"]
            .nunique()
            .reset_index(
                name="attendance_days"
            )
        )
        people = people.merge(
            performance,
            on="person_id",
            how="left"
        )
        people["attendance_days"] = (
            people["attendance_days"]
            .fillna(0)
        )
    return people.sort_values(
        "attendance_days",
        ascending=False
    )

# =====================================================
# HOURLY ATTENDANCE
# =====================================================

def hourly_attendance(attendance_df):
    if attendance_df.empty:
        return pd.DataFrame(
            columns=[
                "hour",
                "attendance"
            ]
        )
    df = attendance_df.copy()
    df["hour"] = df["time"].apply(
        lambda x: x.hour
        if pd.notna(x)
        else None
    )
    result = (
        df.dropna(subset=["hour"])
        .groupby("hour")
        ["person_id"]
        .nunique()
        .reset_index(
            name="attendance"
        )
    )
    result["hour"] = (
        result["hour"]
        .astype(int)
    )
    return result.sort_values("hour")

# =====================================================
# RECENT ATTENDANCE
# =====================================================

def recent_attendance(attendance_df,limit=10):
    if attendance_df.empty:
        return attendance_df
    return (
        attendance_df
        .sort_values(
            ["date", "time"],
            ascending=False
        )
        .head(limit)
        .copy()
    )

# =====================================================
# CSV EXPORT
# =====================================================

def dataframe_to_csv(df):
    return df.to_csv(
        index=False
    ).encode("utf-8")