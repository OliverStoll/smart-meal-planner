import requests
import pandas as pd
import os
from time import sleep


def download_pdf(url, save_path):
    response = requests.get(url)
    assert response.status_code == 200, f"Error in downloading pdf: {response.status_code}"
    assert response.headers['Content-Type'] == 'application/pdf', f"Error in downloading pdf: {response.headers['Content-Type']}"
    assert len(response.content) > 1000, f"Error in downloading pdf: File is empty"
    with open(save_path, 'wb') as f:
        f.write(response.content)



def download_all_pdfs(csv_path='unique_recipes.csv', dir_path = 'pdfs'):
    df = pd.read_csv(csv_path)
    os.makedirs(dir_path, exist_ok=True)
    counter = 0
    for idx, row in df.iterrows():
        print(f"[{idx+1}/{len(df)}] ", end='')
        pdf_title = row['title'].replace(' ', '_').replace(':', ',')
        try:
            download_pdf(row['pdf_link'], f"{dir_path}/{pdf_title}.pdf")
            print(f"Downloaded {row['pdf_link']}")
            counter += 1
        except Exception as e:
            print(f"Error in downloading pdf: {e}")
        # print number of downloaded pdfs in dir_path folder
        print(counter, len(os.listdir(dir_path)))

    print(f"Downloaded {counter} PDFs")


if __name__ == '__main__':
    download_all_pdfs()