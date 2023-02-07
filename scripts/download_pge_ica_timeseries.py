'''
This script downloads ICA timeseries data for each circuit and month-hour combination
from PG&E, using selenium to access the PG&E ICA map.

This script does the following:
* downloads the ICA timeseries for each feeder on the PG&E ICA map, and saves it as a pickled dataframe

To use this script, you need to: (1) have Google Chrome installed on your computer, (2) download the PG&E ICA
geodatabase from https://www.pge.com/b2b/distribution-resource-planning/downloads/integration-capacity/ICADisplay.gdb.zip,
(3) convert the feeder layer of the geodatabase to a shapefile (you can do this using the free software QGIS), and (4)
create a user account to access the ICA map: https://www.pge.com/b2b/distribution-resource-planning/integration-capacity-map.shtml
''' 

### setup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoSuchWindowException
import os
import geopandas as gpd
import pandas as pd
import time
from zipfile import ZipFile
from zipfile import BadZipFile
import numpy as np
import pickle
import glob

############################################## parameters to set by user ###############################################
########################################################################################################################
# file location of feeder-level PG&E ICA shapefile
# e.g. "C:/Users/salma/Box/research/projects/distribution-grid/raw-data/iou_ica/pge/20220211_ICA_Circuit_Segments/ica_feederdetail.shp"
feedershp_dir = ""

# Chrome download folder location; zip files will be downloaded here, read into a dataframe, and then deleted
# e.g. "C:/Users/salma/Downloads/"
download_dir = ""

# folder location in which ICA dataframes should be stored
# e.g. "C:/Users/salma/Box/research/projects/distribution-grid/raw-data/ica_timeseries"
df_dir = ""

# username to log in to ICA map
username = ""

# password to log in to ICA map
password = ""

# set to True to download feeder csvs from PG&E. If download pauses or code stops running, seting download_csvs to
# True will only download ICA timeseries csvs that are not already present in the "df_dir" folder. That is, if you want
# the code to ignore all csvs currently in the "df_dir" folder and redownload everything, you should either delete the
# folder contents or set "df_dir" to point to a new, empty folder
download_csvs = True

# number of times to try entering username to login page before returning error, and to try downloading ICA timeseries
# before returning error
tries = 20
########################################################################################################################

pd.options.display.max_columns = 30

# urls
login_url = "https://www.pge.com/b2b/distribution-resource-planning/integration-capacity-map.shtml"
data_url = "https://www.pge.com/b2b/distribution-resource-planning/downloads/integration-capacity/"

# get list of line section #s from shapefile
ica = gpd.read_file(feedershp_dir)
feeder_id_list = ica.FeederID.to_numpy()

os.chdir(df_dir) # set current directory to where ICA timeseries dataframes should be stored
counter_p = 'counter.p'

def login(driver, login_url, username, password):
    """
    This function logs in to the ICA map.
    
    Inputs:
    driver: Chrome webdriver
    login_url: URL for login page
    username: your username
    password: your password
    
    Returns: nothing
    """
    # log in
    driver.get(login_url)
    time.sleep(2)
    i = 0
    while i < tries:
        try:
            driver.find_element_by_id("username").send_keys(username)
            driver.find_element(By.XPATH, "//input[@placeholder='Password']").send_keys(password)
            driver.find_element_by_id("submit").click()
            break
        except NoSuchElementException:
            i += 1
            time.sleep(2)

    time.sleep(3)

def process_zip(driver, data_url, id):
    """
    This function processes a single zip file downloaded from the ICA map by first downloading the file, then saving
    the csv to a dataframe, then deleting the downloaded zip file.

    Inputs:
    driver: Chrome webdriver
    data_url: url prefix for csv downloads
    id: feeder ID

    Returns: nothing
    """
    # download zip file
    i = 0
    while i < tries:
        try:
            url = data_url + id + ".zip"
            driver.get(url)
            print("downloaded " + id)
            break
        except NoSuchWindowException:
            print("no such window...")
            i += 1
            time.sleep(1)

    # open zipfile and save csv to dataframe
    i = 0
    badzip = False
    while i < tries:
        try:
            print("trying " + id)
            zf = ZipFile(download_dir + id + ".zip")
            print("opened " + id)
            df = pd.read_csv(zf.open(id + ".csv"))
            zf.close()
            break
        except FileNotFoundError:
            i += 1
            time.sleep(2)
        except BadZipFile:
            i = tries
            badzip = True

    # delete zipfile
    i = 0
    while i < tries:
        if ~badzip:
            try:
                print("trying to delete " + id)
                os.remove(download_dir + id + ".zip")
                print("deleted " + id)
                break
            except FileNotFoundError:
                i += 1
                time.sleep(2)

    # save csv to folder
    if ~badzip:
        df.to_csv(id + ".csv", index=False)

def get_csv_list():
    """
    This function determines which feeder IDs have already had their timeseries data downloaded and saved.

    Inputs: none

    Returns: list of feeder IDs with data in folder "df_dir"
    """
    csvs_dl_list = glob.glob(os.getcwd() + "/*.csv")
    csvs_dl_list = [sub.replace(os.getcwd() + "\\", "") for sub in csvs_dl_list]
    csvs_dl_list = [sub.replace(".csv", "") for sub in csvs_dl_list]

    return csvs_dl_list

if download_csvs:
    # if download_csvs is True, then download timeseries for any feeder IDs that do not currently have data in
    # the folder "df_dir"

    # initialize chrome driver
    driver = webdriver.Chrome(ChromeDriverManager().install())

    # log in to ICA map
    login(driver, login_url, username, password)

    # get all the feeder IDs of csvs currently in folder
    csvs_dl = get_csv_list()

    # get list of missing csvs
    csvs_missing = list(set(feeder_id_list.tolist()) - set(csvs_dl))
    print("retrieving " + str(len(csvs_missing)) + " feeder IDs")

    for id in csvs_missing:
        # download, save to dataframe, and delete the zip file for each feeder ID
        print(id)
        process_zip(driver, data_url, id)

    # print final list of missing csvs for manual check
    # get all the feeder IDs of csvs currently in folder
    csvs_dl_final = get_csv_list()

    # get list of missing csvs
    csvs_missing_final = list(set(feeder_id_list.tolist()) - set(csvs_dl_final))
    print("IDs that weren't processed:")
    print(csvs_missing_final)
