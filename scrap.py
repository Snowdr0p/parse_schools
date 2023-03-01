from typing import List, Dict
import aiohttp
import aiofiles
import asyncio
from bs4 import BeautifulSoup
import time
import json
import os

URL_SUBDS = "https://schools.by/subdomains"
URL_TEACHERS = "/teachers"
MAX_RECONNECT_TRIES = 3
SUBFOLDER = "img"
TRANSLATION_TABLE = {
    '/':'_',
    '<':'_',
    '>':'_',
    ':':'_',
    '"':'_',
    '\\':'_',
    '|':'_',
    '?':'_',
    '*':'_',
}


def make_name_valid(name: str) -> str:
    """Removes trailing spacing characters and symbols that are deprecated for file names"""
    name.strip().translate(TRANSLATION_TABLE)


async def download_and_save_image(filename: str, img_url: str, session: aiohttp.ClientSession) -> None:
    """Downloads image from url and saves it in subfolder as filename.jpg"""
    print(f"Downloading image {img_url}.")
    tries = 0
    # download image
    while tries < MAX_RECONNECT_TRIES:
        try:
            async with session.get(img_url) as resp:
                raw = await resp.read()
        except (aiohttp.ServerConnectionError, aiohttp.ClientError, aiohttp.ServerTimeoutError) as err:
            print(f"Got {type(err)}: {err} on {img_url}")
        except asyncio.TimeoutError as err:
            print(f"Got {type(err)}: {err} on {img_url}")
        except UnicodeError as err:
            print(f"Got {type(err)}: {err} on {img_url}")
            return
        else:
            break
        finally:
            tries += 1
    else:
        return
    # save image
    path_to_file = os.path.join(SUBFOLDER, filename + ".jpg")
    async with aiofiles.open(path_to_file, "wb") as afile:
        await afile.write(raw)
    print(f"{path_to_file} saved.")
    

async def parse_teachers_page(page_url: str, session: aiohttp.ClientSession) -> List[Dict]:
    """Parses page with teachers and returns a list of dicts with keys 'name' and 'img_url'
    with corresponding information"""
    teachers = []
    tries = 0
    # get page with teachers
    while tries < MAX_RECONNECT_TRIES:     
        try:
            print(f"Trying to get {page_url}")
            async with session.get(page_url) as resp:
                html = await resp.text()
        except (aiohttp.ServerConnectionError, aiohttp.ClientError, aiohttp.ServerTimeoutError) as err:
            print(f"{type(err)}: {err} on {page_url}")
        except UnicodeError as err:
            print(f"{type(err)}: {err}, got it on {page_url}")
            return []
        else:
            break
        finally:
            tries += 1
    else:
        return []
    # parse page
    soup = BeautifulSoup(html, features="html.parser")
    teachers_cards = soup.select("div.sch_ptbox_item")
    for card in teachers_cards:
        teacher = {}
        # get teacher name
        name = card.select_one("a.user_type_3")
        if name:
            teacher['name'] = make_name_valid(name.text)
        # get teacher img url
        img = card.select_one("a.photo>img")
        if img:
            teacher['img_url'] = img.get('src')
        if teacher:
            teachers.append(teacher)

    print(f"{page_url} parsed. Found {len(teachers)} teachers.")
    return teachers


async def main():
    """main"""
    async with aiohttp.ClientSession() as session:
        # get subdomains
        async with session.get(URL_SUBDS) as resp:
            subds_html = await resp.text()
        
        subds_soup = BeautifulSoup(subds_html, "html.parser")
        divs_city_box = subds_soup.select("div.schlist_city_box")

        subdomains = []
        for div in divs_city_box:
            subdomains.extend(
                a.get("href", "")
                for a in div.select("li > a")
            )

        # write subdomains to file
        async with aiofiles.open("subdomains.txt", "w", encoding="utf-8") as afile:
            for subdomain in subdomains:
                await afile.write(subdomain + "\n")
        
        print(f'Subdomains found: {len(subdomains)}')

        # get teachers
        tasks = []
        for subdomain in subdomains:
            task = asyncio.create_task(parse_teachers_page(subdomain + URL_TEACHERS, session))
            tasks.append(task)

        teachers = []
        img_tasks = []
        for task in tasks:
            res = await task
            if res:
                teachers.extend(res)

                for teacher in res:
                    name = teacher.get('name')
                    img_url = teacher.get('img_url')
                    if name is None or img_url is None:
                        continue
                    img_task = asyncio.create_task(download_and_save_image(name, img_url, session))
                    img_tasks.append(img_task)

        # save teachers to file
        async with aiofiles.open("teachers.json", "w", encoding="utf-8") as afile:
            await afile.write(json.dumps(teachers, ensure_ascii=False))
        
        # wait until all images will be downloaded
        for img_task in img_tasks:
            await img_task
        
        path_to_downloads = os.path.join(os.getcwd(), SUBFOLDER)
        print(f'All images were downloaded into {path_to_downloads}')


# create subdirectory for images
if not os.path.exists(SUBFOLDER):
    os.makedirs(SUBFOLDER)

# parse sites
start = time.time()
asyncio.run(main())
end = time.time()

print(f'Work time: {end - start} s.')
