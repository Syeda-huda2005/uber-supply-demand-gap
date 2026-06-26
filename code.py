import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Set global plot style
sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.figsize'] = (10, 5)
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
print("Libraries imported successfully.")
# Load Dataset
df = pd.read_excel('/content/Uber_EDA_Excel.xlsx')
print("Dataset loaded successfully.")
print(f"Shape: {df.shape}")
# Dataset First Look
df.head(10)
# Dataset Rows & Columns count
print(f"Number of Rows    : {df.shape[0]}")
print(f"Number of Columns : {df.shape[1]}")
# Dataset Info
df.info()
# Dataset Duplicate Value Count
print(f"Number of duplicate rows: {df.duplicated().sum()}")
# Missing Values/Null Values Count
print(df.isnull().sum())
print(f"\nTotal missing values: {df.isnull().sum().sum()}")
# Visualizing the missing values
plt.figure(figsize=(8, 4))
missing = df.isnull().sum()
missing = missing[missing > 0]
missing.plot(kind='bar', color=['#e74c3c', '#e67e22'], edgecolor='black')
plt.title('Missing Values per Column', fontsize=14)
plt.ylabel('Count')
plt.xticks(rotation=0)
for i, v in enumerate(missing):
    plt.text(i, v + 30, str(v), ha='center', fontweight='bold')
plt.tight_layout()
plt.show()
# Dataset Columns
print("Column Names:")
for col in df.columns:
    print(f"  - {col}")
    # Dataset Describe
df.describe(include='all')
# Check Unique Values for each variable
for col in df.columns:
    print(f"{col}: {df[col].nunique()} unique values")
    if df[col].nunique() <= 5:
        print(f"  Values: {df[col].unique().tolist()}")
        # Write your code to make your dataset analysis ready.

# --- Step 1: Parse mixed-format timestamps ---
# The previous parse_ts function was failing to correctly convert string timestamps
# to datetime objects, leading to NaT values and subsequent errors.
# We will use pd.to_datetime directly on the Series, which is more efficient
# and robust for various formats by setting dayfirst=True to handle DD/MM/YYYY.
df['Request Timestamp'] = pd.to_datetime(df['Request Timestamp'], dayfirst=True, errors='coerce')
df['Drop Timestamp']    = pd.to_datetime(df['Drop Timestamp'], dayfirst=True, errors='coerce')

# --- Handle unparseable Request Timestamps ---
# Drop rows where 'Request Timestamp' could not be parsed (resulting in NaT)
# This directly addresses the 'NaN' error in Request_Hour and ensures data integrity for time-based features.
initial_rows = df.shape[0]
df.dropna(subset=['Request Timestamp'], inplace=True)
print(f"Dropped {initial_rows - df.shape[0]} rows due to unparseable 'Request Timestamp'.")

# --- Step 2: Extract time features ---
df['Request_Hour']    = df['Request Timestamp'].dt.hour
df['Request_Day']     = df['Request Timestamp'].dt.day
df['Request_Weekday'] = df['Request Timestamp'].dt.day_name()

# --- Step 3: Define time-of-day slots ---
def time_slot(hour):
    if 5 <= hour < 10:
        return 'Morning Rush (5-10)'
    elif 10 <= hour < 17:
        return 'Daytime (10-17)'
    elif 17 <= hour < 22:
        return 'Evening Rush (17-22)'
    else:
        return 'Late Night (22-5)'

df['Time_Slot'] = df['Request_Hour'].apply(time_slot)

# --- Step 4: Trip duration (for completed trips) ---
df['Trip_Duration_min'] = (df['Drop Timestamp'] - df['Request Timestamp']).dt.total_seconds() / 60

# --- Step 5: Binary flag for fulfilled requests ---
df['Is_Fulfilled'] = (df['Status'] == 'Trip Completed').astype(int)

print("Data wrangling complete. New columns added:")
print(df[['Request_Hour','Time_Slot','Trip_Duration_min','Is_Fulfilled']].head(5))
# Running SQL queries directly inside the notebook using SQLite
import sqlite3
import pandas as pd

# Load cleaned data into an in-memory SQLite database
df_sql = pd.read_excel('/content/Uber_EDA_Excel.xlsx')

# Apply the same robust timestamp parsing to df_sql
df_sql['Request Timestamp'] = pd.to_datetime(df_sql['Request Timestamp'], dayfirst=True, errors='coerce')
df_sql['Drop Timestamp']    = pd.to_datetime(df_sql['Drop Timestamp'], dayfirst=True, errors='coerce')

# --- Handle unparseable Request Timestamps for df_sql ---
# Drop rows where 'Request Timestamp' could not be parsed (resulting in NaT)
initial_sql_rows = df_sql.shape[0]
df_sql.dropna(subset=['Request Timestamp'], inplace=True)
print(f"Dropped {initial_sql_rows - df_sql.shape[0]} rows from df_sql due to unparseable 'Request Timestamp'.")

df_sql['Request_Hour']      = df_sql['Request Timestamp'].dt.hour
df_sql['Request_Weekday']   = df_sql['Request Timestamp'].dt.day_name()
df_sql['Trip_Duration_min'] = (df_sql['Drop Timestamp'] - df_sql['Request Timestamp']).dt.total_seconds() / 60

def time_slot(h):
    if 5 <= h < 10:    return 'Morning Rush (5-10)'
    elif 10 <= h < 17: return 'Daytime (10-17)'
    elif 17 <= h < 22: return 'Evening Rush (17-22)'
    else:              return 'Late Night (22-5)'

df_sql['Time_Slot']    = df_sql['Request_Hour'].apply(time_slot)
df_sql['Is_Fulfilled'] = (df_sql['Status'] == 'Trip Completed').astype(int)

# Drop original columns that are replaced by the new feature-engineered columns
# to avoid duplicate column names after renaming.
cols_to_drop = ['Hour', 'Weekday', 'Trip Duration (min)', 'Time Slot', 'Fulfilled?']
existing_cols_to_drop = [col for col in cols_to_drop if col in df_sql.columns]
if existing_cols_to_drop:
    df_sql = df_sql.drop(columns=existing_cols_to_drop)

# Rename columns to match SQL schema
df_sql.columns = [c.lower().replace(' ', '_') for c in df_sql.columns]

conn = sqlite3.connect(':memory:')
df_sql.to_sql('uber_requests', conn, index=False, if_exists='replace')
print("SQLite DB ready with", pd.read_sql("SELECT COUNT(*) as rows FROM uber_requests", conn).iloc[0,0], "rows")
# SQL — Problem Statement 1: Overall Status Distribution
query1 = '''
SELECT
    status,
    COUNT(*) AS total_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM uber_requests), 2) AS percentage
FROM uber_requests
GROUP BY status
ORDER BY total_count DESC
'''
print("PS-1: Overall Status Distribution")
print(pd.read_sql(query1, conn).to_string(index=False))
# SQL — Problem Statement 2: Status by Pickup Point
query2 = '''
SELECT
    pickup_point,
    status,
    COUNT(*) AS count
FROM uber_requests
GROUP BY pickup_point, status
ORDER BY pickup_point, count DESC
'''
print("PS-2: Status by Pickup Point")
print(pd.read_sql(query2, conn).to_string(index=False))
# SQL — Problem Statement 3 & 4: Cancellation Rate by Hour (City)
query3 = '''
SELECT
    request_hour,
    COUNT(*) AS total_city_requests,
    SUM(CASE WHEN status = "Cancelled" THEN 1 ELSE 0 END) AS cancellations,
    ROUND(SUM(CASE WHEN status = "Cancelled" THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS cancel_rate_pct
FROM uber_requests
WHERE pickup_point = "City"
GROUP BY request_hour
ORDER BY cancel_rate_pct DESC
LIMIT 8
'''
print("PS-4: Top Hours with Highest Cancellation Rate (City Pickups)")
print(pd.read_sql(query3, conn).to_string(index=False))
# SQL — Problem Statement 5: No Cars Rate at Airport by Hour
query4 = '''
SELECT
    request_hour,
    COUNT(*) AS total_airport_requests,
    SUM(CASE WHEN status = "No Cars Available" THEN 1 ELSE 0 END) AS no_cars_count,
    ROUND(SUM(CASE WHEN status = "No Cars Available" THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS no_cars_rate_pct
FROM uber_requests
WHERE pickup_point = "Airport"
GROUP BY request_hour
ORDER BY no_cars_rate_pct DESC
LIMIT 8
'''
print("PS-5: Top Hours with Highest No-Cars Rate (Airport Pickups)")
print(pd.read_sql(query4, conn).to_string(index=False))
# SQL — Problem Statement 11: The Two Critical Problem Windows
query5 = '''
SELECT "City Morning Rush Cancellations" AS problem_window,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM uber_requests), 2) AS pct_of_total
FROM uber_requests
WHERE pickup_point = "City"
  AND time_slot = "Morning Rush (5-10)"
  AND status = "Cancelled"
UNION ALL
SELECT "Airport Evening Rush No Cars" AS problem_window,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM uber_requests), 2) AS pct_of_total
FROM uber_requests
WHERE pickup_point = "Airport"
  AND time_slot = "Evening Rush (17-22)"
  AND status = "No Cars Available"
'''
print("PS-11: The Two Critical Problem Windows")
result = pd.read_sql(query5, conn)
print(result.to_string(index=False))
total_pct = result['pct_of_total'].sum()
print(f"\nCombined: {total_pct:.1f}% of ALL requests are from just these 2 problem windows!")
# Chart - 1: Status Distribution (Pie + Bar)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

status_counts = df['Status'].value_counts()
colors = ['#2ecc71', '#e74c3c', '#e67e22']

# Pie
axes[0].pie(status_counts, labels=status_counts.index, autopct='%1.1f%%',
            colors=colors, startangle=140, wedgeprops={'edgecolor':'white','linewidth':1.5})
axes[0].set_title('Proportion of Request Statuses')

# Bar
status_counts.plot(kind='bar', ax=axes[1], color=colors, edgecolor='black')
axes[1].set_title('Count of Request Statuses')
axes[1].set_xlabel('Status')
axes[1].set_ylabel('Number of Requests')
axes[1].tick_params(axis='x', rotation=15)
for p in axes[1].patches:
    axes[1].annotate(str(int(p.get_height())),
                     (p.get_x() + p.get_width()/2, p.get_height() + 30),
                     ha='center', fontweight='bold')

plt.suptitle('Overall Uber Request Status', fontsize=15, fontweight='bold')
plt.tight_layout()
plt.show()
# Chart - 2: Status by Pickup Point (Stacked Bar)
ct = pd.crosstab(df['Pickup Point'], df['Status'])
ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100

ct_pct.plot(kind='bar', stacked=True, figsize=(9, 5),
            color=['#e67e22', '#e74c3c', '#2ecc71'], edgecolor='white')
plt.title('Request Status Distribution by Pickup Point (%)', fontsize=14)
plt.xlabel('Pickup Point')
plt.ylabel('Percentage (%)')
plt.xticks(rotation=0)
plt.legend(title='Status', bbox_to_anchor=(1.01, 1))
plt.tight_layout()
plt.show()

print(ct)
# Chart - 3: Hourly Demand (Request Volume by Hour)
plt.figure(figsize=(12, 5))
hourly = df.groupby('Request_Hour').size().reset_index(name='Requests')
sns.lineplot(data=hourly, x='Request_Hour', y='Requests', marker='o', linewidth=2.5, color='#2980b9')
plt.fill_between(hourly['Request_Hour'], hourly['Requests'], alpha=0.15, color='#2980b9')
plt.axvspan(5, 9.5, alpha=0.1, color='red', label='Morning Rush')
plt.axvspan(17, 21.5, alpha=0.1, color='orange', label='Evening Rush')
plt.title('Hourly Distribution of Ride Requests', fontsize=14)
plt.xlabel('Hour of Day')
plt.ylabel('Number of Requests')
plt.xticks(range(0, 24))
plt.legend()
plt.tight_layout()
plt.show()
# Chart - 4: Heatmap - Hour vs Status Count
pivot = df.pivot_table(index='Status', columns='Request_Hour', aggfunc='size', fill_value=0)
plt.figure(figsize=(16, 4))
sns.heatmap(pivot, cmap='YlOrRd', linewidths=0.3, annot=True, fmt='.0f', annot_kws={'size': 7})
plt.title('Request Count by Status and Hour of Day', fontsize=14)
plt.xlabel('Hour of Day')
plt.ylabel('Status')
plt.tight_layout()
plt.show()
# Chart - 5: Cancellations by Pickup Point and Hour
cancelled = df[df['Status'] == 'Cancelled']
no_cars   = df[df['Status'] == 'No Cars Available']

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

for ax, sub, title, color in zip(
    axes,
    [cancelled, no_cars],
    ['Cancellations by Hour & Pickup', 'No Cars Available by Hour & Pickup'],
    ['#e74c3c', '#e67e22']
):
    for pt, ls in [('City', '-'), ('Airport', '--')]:
        data = sub[sub['Pickup Point'] == pt].groupby('Request_Hour').size()
        ax.plot(data.index, data.values, marker='o', linestyle=ls, label=pt, linewidth=2)
    ax.set_title(title)
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Count')
    ax.set_xticks(range(0, 24))
    ax.legend()
    ax.grid(True, alpha=0.4)

plt.tight_layout()
plt.show()
# Chart - 6: Time Slot vs Status (Grouped Bar)
slot_order = ['Morning Rush (5-10)', 'Daytime (10-17)', 'Evening Rush (17-22)', 'Late Night (22-5)']
ct2 = pd.crosstab(df['Time_Slot'], df['Status']).reindex(slot_order)

ct2.plot(kind='bar', figsize=(12, 5), color=['#e67e22','#e74c3c','#2ecc71'], edgecolor='black')
plt.title('Request Status by Time Slot', fontsize=14)
plt.xlabel('Time Slot')
plt.ylabel('Number of Requests')
plt.xticks(rotation=15)
plt.legend(title='Status')
for p in plt.gca().patches:
    if p.get_height() > 0:
        plt.gca().annotate(str(int(p.get_height())),
                           (p.get_x() + p.get_width()/2, p.get_height() + 10),
                           ha='center', fontweight='bold')
plt.tight_layout()
plt.show()
# Chart - 7: Fulfillment Rate by Pickup Point and Time Slot
fulfil = df.groupby(['Pickup Point', 'Time_Slot'])['Is_Fulfilled'].mean().reset_index()
fulfil['Fulfillment Rate (%)'] = fulfil['Is_Fulfilled'] * 100
fulfil['Time_Slot'] = pd.Categorical(fulfil['Time_Slot'], categories=slot_order, ordered=True)
fulfil = fulfil.sort_values('Time_Slot')

plt.figure(figsize=(12, 5))
sns.barplot(data=fulfil, x='Time_Slot', y='Fulfillment Rate (%)', hue='Pickup Point',
            palette=['#3498db', '#e74c3c'])
plt.title('Fulfillment Rate (%) by Pickup Point & Time Slot', fontsize=14)
plt.xlabel('Time Slot')
plt.ylabel('Fulfillment Rate (%)')
plt.ylim(0, 100)
plt.axhline(50, color='grey', linestyle='--', label='50% line')
plt.legend()
plt.xticks(rotation=10)
plt.tight_layout()
plt.show()
# Chart - 8: Trip Duration Distribution (Box + Violin)
completed = df[df['Status'] == 'Trip Completed'].copy()

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

sns.boxplot(data=completed, x='Pickup Point', y='Trip_Duration_min',
            palette='Set2', ax=axes[0])
axes[0].set_title('Trip Duration by Pickup Point (Box)')
axes[0].set_ylabel('Duration (minutes)')

sns.violinplot(data=completed, x='Pickup Point', y='Trip_Duration_min',
               palette='Set2', ax=axes[1], inner='quartile')
axes[1].set_title('Trip Duration by Pickup Point (Violin)')
axes[1].set_ylabel('Duration (minutes)')

plt.suptitle('Distribution of Completed Trip Durations', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

print(completed.groupby('Pickup Point')['Trip_Duration_min'].describe().round(1))
# Chart - 9: Day-wise Request Volume
day_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
day_counts = df.groupby('Request_Weekday').size().reindex(day_order)

plt.figure(figsize=(10, 5))
bars = plt.bar(day_counts.index, day_counts.values,
               color=sns.color_palette('viridis', 7), edgecolor='black')
for bar in bars:
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
             str(bar.get_height()), ha='center', fontweight='bold')
plt.title('Total Ride Requests by Day of Week', fontsize=14)
plt.xlabel('Day')
plt.ylabel('Number of Requests')
plt.tight_layout()
plt.show()
# Chart - 10: Supply-Demand Gap Bar (by Hour)
hourly_status = df.groupby(['Request_Hour', 'Status']).size().unstack(fill_value=0)
hourly_status['Demand'] = hourly_status.sum(axis=1)
hourly_status['Supply'] = hourly_status.get('Trip Completed', 0)
hourly_status['Gap'] = hourly_status['Demand'] - hourly_status['Supply']

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(hourly_status.index, hourly_status['Demand'], label='Total Demand', color='#3498db', alpha=0.7)
ax.bar(hourly_status.index, hourly_status['Supply'], label='Fulfilled (Supply)', color='#2ecc71', alpha=0.9)
ax.plot(hourly_status.index, hourly_status['Gap'], color='red', marker='D',
        linewidth=2, label='Gap (Unfulfilled)')
ax.set_title('Supply vs Demand Gap by Hour', fontsize=14)
ax.set_xlabel('Hour of Day')
ax.set_ylabel('Number of Requests')
ax.set_xticks(range(0, 24))
ax.legend()
plt.tight_layout()
plt.show()
# Chart - 11: Cancellation Rate by Hour (City only)
city_df = df[df['Pickup Point'] == 'City']
city_hourly = city_df.groupby('Request_Hour')['Status'].value_counts().unstack(fill_value=0)
city_hourly['Cancel_Rate'] = city_hourly.get('Cancelled', 0) / city_hourly.sum(axis=1) * 100

plt.figure(figsize=(12, 5))
plt.fill_between(city_hourly.index, city_hourly['Cancel_Rate'],
                 alpha=0.4, color='#e74c3c')
plt.plot(city_hourly.index, city_hourly['Cancel_Rate'],
         color='#e74c3c', marker='o', linewidth=2)
plt.axhspan(0, 10, alpha=0.05, color='green', label='Acceptable (<10%)')
plt.title('Driver Cancellation Rate by Hour (City Pickups)', fontsize=14)
plt.xlabel('Hour of Day')
plt.ylabel('Cancellation Rate (%)')
plt.xticks(range(0, 24))
plt.legend()
plt.tight_layout()
plt.show()
# Chart - 12: No-Cars Rate at Airport by Hour
airport_df = df[df['Pickup Point'] == 'Airport']
ap_hourly = airport_df.groupby('Request_Hour')['Status'].value_counts().unstack(fill_value=0)
ap_hourly['NoCar_Rate'] = ap_hourly.get('No Cars Available', 0) / ap_hourly.sum(axis=1) * 100

plt.figure(figsize=(12, 5))
plt.fill_between(ap_hourly.index, ap_hourly['NoCar_Rate'],
                 alpha=0.4, color='#e67e22')
plt.plot(ap_hourly.index, ap_hourly['NoCar_Rate'],
         color='#e67e22', marker='s', linewidth=2)
plt.title('No Cars Available Rate by Hour (Airport Pickups)', fontsize=14)
plt.xlabel('Hour of Day')
plt.ylabel('No Cars Rate (%)')
plt.xticks(range(0, 24))
plt.tight_layout()
plt.show()
# Chart - 13: Multivariate - Pickup Point x Time Slot x Status (Heatmap)
multi = df.groupby(['Pickup Point', 'Time_Slot', 'Status']).size().reset_index(name='Count')
multi['Time_Slot'] = pd.Categorical(multi['Time_Slot'], categories=slot_order, ordered=True)

pivot3 = multi.pivot_table(index=['Pickup Point', 'Status'], columns='Time_Slot', values='Count', fill_value=0)
pivot3 = pivot3[slot_order]

plt.figure(figsize=(14, 7))
sns.heatmap(pivot3, annot=True, fmt='.0f', cmap='Blues', linewidths=0.4, annot_kws={'size': 10})
plt.title('Request Count: Pickup Point × Status × Time Slot', fontsize=14)
plt.tight_layout()
plt.show()
# Correlation Heatmap visualization code
corr_df = df[['Request_Hour', 'Is_Fulfilled', 'Trip_Duration_min', 'Driver ID']].copy()
corr_df['Has_Driver'] = df['Driver ID'].notna().astype(int)
corr_df = corr_df.drop(columns='Driver ID')
corr_df['Is_Airport'] = (df['Pickup Point'] == 'Airport').astype(int)

plt.figure(figsize=(7, 5))
sns.heatmap(corr_df.corr(), annot=True, fmt='.2f', cmap='coolwarm',
            center=0, linewidths=0.5)
plt.title('Correlation Heatmap of Numerical Features', fontsize=14)
plt.tight_layout()
plt.show()
# Pair Plot visualization code
pair_df = df[df['Status'] == 'Trip Completed'][['Request_Hour', 'Trip_Duration_min']].copy()
pair_df['Pickup point'] = df[df['Status'] == 'Trip Completed']['Pickup Point']

sns.pairplot(pair_df, hue='Pickup point', palette={'City':'#3498db', 'Airport':'#e74c3c'},
             plot_kws={'alpha': 0.5}, diag_kind='kde')
plt.suptitle('Pair Plot: Completed Trips by Pickup Point', y=1.02, fontsize=13)
plt.tight_layout()
plt.show()
