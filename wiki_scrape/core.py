# Inspiration from https://www.kaggle.com/datasets/muhajipra/people-of-skyrim
import bs4 as bs
import urllib.request
import pandas as pd

def get_category_pages(root_path, category):
    category_path = root_path + '/wiki/Category:' + category
    sauce = urllib.request.urlopen(category_path).read()
    soup = bs.BeautifulSoup(sauce, "lxml")
    pages = []
    for group in soup.find_all(class_='mw-category-group'):
        subgroup = group.find_all('a')
        for row in subgroup:
            # name = row.get('title')
            url = root_path + row.get('href')
            pages.append(url)
            # pages.append((name, url))

    return(pages)

# Get a single page's data
def get_page_data(page_url):
# TODO: Get the following information eventually and potentially in many tables:
# URL (ID), Title, Name, Description, "Details", Story Involvement, Event Involvement, Dialogue
    page_info = {}
    sauce = urllib.request.urlopen(page_url).read()
    soup = bs.BeautifulSoup(sauce, "lxml")
    page_info['URL'] = page_url
    page_info['Title'] = soup.find(id = 'firstHeading').get_text().strip()
    info_box = soup.find('div', class_='infobox')
    if info_box is not None:
        # Get their name
        page_info['Name'] = info_box.find(class_='heading').get_text().strip()
        page_info['Description'] = info_box.find_next_sibling('p').get_text().strip()
        # Get their details
        # get all dt/dd pairs. This uses list comprehension to creat list of text for each element
        # It ends up being value, pairs... 'Race': 'Human', 'Level': '11'...
        details = dict(zip([k.get_text().strip() for k in info_box.find_all('dt')],
                           [v.get_text().strip() for v in info_box.find_all('dd')]))
        for k, v in details.items():
# TODO: Some keys have multiple values (location). This should be broken out somehow.
            page_info[k] = v

    return(page_info)

# Get story involvement (breaking it out because it is a bit involved)
#TODO: does story involvement need to be their own table?
def get_story_involvement(page_url, page_soup):
    # This should be organized in the following way:
        # [{ 'Story': 'Personal Story', 'Chapter': 'Chapter 2', 'Path': 'Some path', 'Name': 'Thicker Than Water' }, ... ]
    all_involvements = []
    for tag in page_soup.find(id = 'Story_involvement').find_parent('h2').next_siblings:
        if tag.name == 'h2':
            # This is no longer the story involvement section
            break
        else:
            # This is an involvement
            if tag.name == 'h3':
                # This is the beginning of a new involvement
                the_story = tag.get_text().strip()
            elif tag.name == 'ul':
                # This is where all the chapter, path, and mission name information is stored for that story
                for subtag in tag.find_all('li', recursive=False):
                    # This is a new chapter
                    the_chapter = subtag.get_text().strip()
                    for subsection in subtag.find('ul').find_all('li', recursive=False):
                        # This should be path or mission (path with have another ul under it)
                        # In the case of a path, we will identify it, else we will ignore path
                        if subsection.find('ul', recursive=False):
                            # This is a path
                            the_path = subsection.get_text().strip()
                            for path_mission in subsection.find('ul').find_all('li', recursive=False):
                                # This is a mission
                                the_mission = path_mission.get_text().strip()
                                all_involvements.append({'Story': the_story,
                                                         'Chapter': the_chapter,
                                                         'Mission': the_mission})
                        else:
                            # This is a mission
                            the_mission = subsection.get_text()
                            all_involvements.append({'Story': the_story,
                                                     'Chapter': the_chapter,
                                                     'Mission': the_mission})
            else:
                # This is something else which I don't understand and we should skip for now.
                break

    return(all_involvements)

# Get all pages data (one page at a time)
def get_data_from_pages(page_urls):
    page_infos = []
    for page_url in page_urls:
        page_infos.append(get_page_data(page_url))

    return(page_infos)

def main(root_path, category):
    pages = get_category_pages(root_path, category)
    # page_details = get_page_data(pages[2])
    page_details = get_data_from_pages(pages[2:3])
    # page_details = get_data_from_pages(pages)
    df = pd.DataFrame(page_details)
    # print("saving to file: /test_file.csv")
    # df.to_csv('test_file.csv', index = False, header = True)
    print(df)

if __name__ == "__main__":
    main('https://wiki.guildwars2.com', "story_characters")

    # categories to check:
    # story_characters
    # All "NPCs_by_rank" below
        # Normal_NPCs
        # Veteran_NPCs
        # Elite_NPCs
        # Epic_NPCs
        # Legendary_NPCs
        # Ambient_creatures