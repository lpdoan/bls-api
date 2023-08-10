# import required libraries
import requests
import pandas as pd
import json
from pprint import pprint
import time
from datetime import date, datetime as dt, timedelta
import openpyxl
from openpyxl import load_workbook, Workbook # export and save data to "output" excel file

# Here we define the list of series of data that we would like to retrieve 
# These series are related to the manufacturing industry i.e. raw metals, freight tracking, ...
series_id = ['PCU322211322211','CUUR0000SA0','WPSFD4131','PCU4841214841212','PCU21232-21232-','WPUID69115','WPU0613','WPU061303','PCUOMFG--OMFG--','WPU03THRU15','WPU301301']

headers = {
           "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36',
           'Content-type': 'application/json'}
           
# Setting up the "year" parameter for the API request
endyear = dt.now().year # end year is always current year 
startyear = endyear - 1 # startyear is previous year 

data = json.dumps({"seriesid": series_id,"startyear":str(startyear), "endyear":str(endyear)})

p = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data, headers=headers)
json_data = json.loads(p.text)

# create main df to contain all data from all series
df = pd.DataFrame(columns = ["series_id", "year","period","value","real/preliminary"])
# create smaller dfs (df1) for each series then append to the main df (df)
for series in json_data["Results"]["series"]:
    seriesId = series["seriesID"] 
    for item in series["data"]:
        year = item['year']
        period = item['period']
        value = item['value']
        footnotes=""
        for footnote in item['footnotes']:
            if footnote:
                footnotes = footnotes + footnote['text'] + ','
        if 'M01' <= period <= 'M12':
            dict = {"series_id": [seriesId],
                    "year": [int(year)], 
                    "period": [period],
                    "value": [float(value)],
                    "real/preliminary": [footnotes[0:-1]]}
        #print(dict)
        df1 = pd.DataFrame.from_dict(dict)
        #print(df1)
        # append data with each loop
        df = df.append(df1, ignore_index = True)   

# Update name mapping for months e.g., show "January" instead of "M01"
df["period"] = df["period"].replace(
    ["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10", "M11", "M12"],
    ['Jan-', 'Feb-', 'Mar-', 'Apr-', 'May-', 'Jun-', 'Jul-', 'Aug-', 'Sep-', 'Oct-', 'Nov-', 'Dec-'])

# combine year and period into one column 
df["period"] = df["period"] + df["year"].astype(str)
df["period"] = [dt.strptime(date, "%b-%Y").strftime("%b-%y") for date in df["period"]]
df["period"] = pd.to_datetime(df["period"], format = "%b-%y")

# remove year  column
df.drop(["year"], axis = 1, inplace=True)

df = df.pivot(index = "period", 
              columns = "series_id",
              values = ["value", "real/preliminary"])

# sort by latest period
df = df.sort_index(ascending = True)

# change dt index to Jan-22 format
df.index = pd.to_datetime(df.index, format = "%b-%y").strftime("%b-%y")
df.index

values_df = df["value"]

values_df = values_df[series_id]

# change ordering
status_df = df["real/preliminary"]

final_df = pd.concat([values_df, status_df], keys = ["values", "real/preliminary"], axis = 1)

# create file path
wb = openpyxl.Workbook()
BLS_ws = wb.active
BLS_ws.title = "all_BLS"
BLS_path = "./output/" + "webscraping_BLS_" + dt.now().strftime("%d-%m-%Y") + ".xlsx"
wb.save(BLS_path)

# write to file
BLS_obj = openpyxl.load_workbook(BLS_path)
writer = pd.ExcelWriter(BLS_path, engine = "openpyxl")
final_df.to_excel(writer, sheet_name = "BLS")
writer.close()
