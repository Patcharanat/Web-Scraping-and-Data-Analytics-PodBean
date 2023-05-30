import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import requests
from seleniumwire import webdriver
import json
import re
import matplotlib.pyplot as plt
import seaborn as sns

url_xml = "https://feed.podbean.com/eighthalf/feed.xml"

content_xml = requests.get(url_xml)
soup_xml = BeautifulSoup(content_xml.text, 'xml')

xml_dict = {} # This dict will be used for mapping data to HTML,AJAX method and aggregated into one DataFrame
for e in soup_xml.find_all('item') : # get all tags 'item'
    temp_url = e.find_next('enclosure')['url'] # get url link to each podcast
    author = e.find_next('itunes:author').text # get the author name
    duration = e.find_next('itunes:duration').text # get duration of each podcast

    # Extract Podcast ID from each URL by regular expression
    test_list = [] # temporary list for extracting podcast ID from URL
    for m in re.finditer('/', temp_url):
        test_list.append(m) # collect all index of '/' string
    ind = test_list[-1].end() # choose the last index of '/'
    temp_id = temp_url[ind:] # slice to get all string after the last '/'
    xml_dict[temp_id] = [author, duration] # Collect ID as key and collect author, duration as list value
len(xml_dict.keys()) # print number of IDs

data = {'ID': [],
        'title': [],
        'date': [],
        'description': []
        } # dict for collecting data
total_download = {}

i = 1
while i < 10_000 : # end at page 124 approximately
    if i < 2 :
        url = "https://eighthalf.podbean.com"
    else :
        url = f"https://eighthalf.podbean.com/page/{i}/"
    i+= 1

    html = requests.get(url)

    if html.status_code == 200 :
    
        soup = BeautifulSoup(html.text, 'html.parser')

        # Retrive Data from AJAX Requests (API Calls) using Selenium-wire.
        driver = webdriver.Chrome()

        driver.get(url)

        # Access requests via attribute `requests` 
        for request in driver.requests:
            if request.response:
                if 'https://www.podbean.com/api2/public/filesPlays?' in request.url :
                    api_url = request.url # collect unique api url everytime new page load.
                    # print(api_url)
                    break # found api url

        driver.quit()

        # access data in api_url
        response = requests.get(api_url)
        download_dict = json.loads(response.text)

        # Collect progressing data
        for e in soup.find_all('div', class_='entry') : # each e is a tag <div> for each podcast
            
            # Collect BeautifulSoup Data
            data['ID'].append(e.find_next('span', class_='hits wait-load')['data-file'])
            data['title'].append(e.h2.text)
            data['date'].append(e.find(class_='day').text)
            data['description'].append(e.find(class_='date').find_next('p').text)
            # break

        # Collect Selenium Data
        total_download.update(download_dict['data']) # update dict by collected data
    else :
        break # will break when no more podcast is shown

df = pd.DataFrame(data) # Transform data from scraping HTML, AJAX webpages to DataFrame

df['download'] = np.nan
df['author'] = np.nan
df['duration'] = np.nan

for index, row in df.iterrows():
    # HTML: Insert download reccord
    ID = df['ID'][index]
    if ID in total_download :
        df['download'][index] = total_download[row['ID']]
    else :
        df['download'][index] = np.nan
    
    # XML: Insert author and duration
    if ID in xml_dict.keys() :
        df['author'][index] = xml_dict[ID][0]
        df['duration'][index] = xml_dict[ID][1]
    else :
        df['author'][index] = np.nan
        df['duration'][index] = np.nan

# due to extremely long run-time, so save data as csv file for next time analysis
df.to_csv('8half_dataset.csv')

df = pd.read_csv('8half_dataset.csv')

df['duration_sec'] = np.nan
df['year'] = np.nan
df['month'] = np.nan

for index, row in df.iterrows():
    # duration_sec
    temp_duration = str(row['duration']).split(sep=':')
    if len(temp_duration) == 3:
        df['duration_sec'][index] = (int(temp_duration[0])*60 + int(temp_duration[1]))*60 + int(temp_duration[2])
    elif len(temp_duration) == 2:
        df['duration_sec'][index] = int(temp_duration[0])*60 + int(temp_duration[1])
    
    # year & month columns
    date_list = str(row['date']).split()
    df['month'][index] = date_list[0]
    df['year'][index] = str(int(date_list[2]))


month_dict = {
    'January': '01',
    'February': '02',
    'March': '03',
    'April': '04',
    'May': '05',
    'June': '06',
    'July': '07',
    'August': '08',
    'September': '09',
    'October': '10',
    'November': '11',
    'December': '12'
}

df.replace({'date': month_dict}, inplace=True, regex=True)
df['date'].replace(',', '', inplace=True, regex=True)
df['date'].replace(' ', '-', inplace=True, regex=True)
df['date'] = pd.to_datetime(df['date'])

df.to_csv('8half_dataset.csv')