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
    page_info['URL'] = page_url.strip()
    page_info['Title'] = soup.find(id='firstHeading').get_text().strip()

    # Parse up to the TOC. Everything after the TOC should be based on the contents of the TOC.
    for tag in soup.find(id='mw-content-text').find('div', class_='mw-parser-output').children:
        #print(tag)
        # Ignore navigable strings
        if isinstance(tag, bs.element.NavigableString):
            continue
        if tag.name == 'h2':
            break
        # Skip the infobox
        if tag.name == 'div':
            if 'class' in tag.attrs.keys() and 'infobox' not in tag['class']:
                # Set the TOC to something else
                if 'id' in tag.attrs.keys() and 'toc' in tag['id']:
                    # This is the toc, let's store that for later parsing
                    page_info['TOC'] = tag
                # Else, just add it to the list of description items
                else:
                    if 'Description' in page_info.keys():
                        page_info['Description'].append(tag)
                    else:
                        page_info['Description'] = [tag]
            else:
                # This is the infobox (multiple infoboxes will mess this up)
                page_info['InfoBox'] = tag
        # Else we will consider this as part of the description and add it.
        elif 'Description' in page_info.keys():
            page_info['Description'].append(tag)
        else:
            page_info['Description'] = [tag]

        #     if 'spoiler-notice' in tag['class']:
        #         # This is the overall spoiler text (states that there are spoilers and for what story)
        #         if 'SpoilerAlert' in page_info.keys():
        #             page_info['SpoilerAlert'].append(tag)
        #         else:
        #             page_info['SpoilerAlert'] = [tag]
        # elif tag.name == 'table':
        #     if 'expandable' in tag['class']:
        #         # This is the actual spoiler hidden spoiler
        #         if 'SpoilerText' in page_info.keys():
        #             page_info['SpoilerText'].append(tag)
        #         else:
        #             page_info['SpoilerText'] = [tag]
        # elif tag.name == 'p':
            # This is the text for this section (description)

    # Parse the remainder of the page based on the TOC.
    sections = {}
    if 'TOC' in page_info.keys():
        print("TOC FOUND")
        # Use the TOC to determine which sections we need to parse
        for tag in page_info['TOC'].find('ul').children:
            if isinstance(tag, bs.element.NavigableString):
                continue
            if tag.name == 'li' and 'class' in tag.attrs.keys() and 'toclevel-1' in tag['class']:
                #sections[tag['href']] = tag.get_text().strip()
                sections[tag.find('a')['href'].replace("#", "")] = tag.find('span', class_='toctext').get_text().strip()
    else:
        # There is no TOC and we should loop through each h2 heading to determine what to do
        print("NO TOC")
        for tag in soup.find('div', class_='mw-parser-output').children:
            if isinstance(tag, bs.element.NavigableString):
                continue
            #print(tag)
            if tag.name == 'h2':
                headline = tag.find_next('span', class_='mw-headline')
                if 'id' in headline.attrs.keys():
                    sections[headline['id']] = headline.get_text().strip()
        print(sections)

    for k in sections.keys():
        # Go to the beginning of that section
        for tag in soup.find(id=k).next_siblings:
            if isinstance(tag, bs.element.NavigableString):
                continue
            if tag.name == 'h2':
                break
            else:
                if k in page_info.keys():
                    page_info[k].append(tag)
                else:
                    page_info[k] = [tag]

    return(page_info)


# TODO: Make a function to pull out all the info from the infobox
# THIS FUNCTION IS JUST A PLACEHOLDER!
def parse_infobox(infobox_html):
    # info_box was the text only way to parse.
    # We should keep it as html and parse it that way to pull out multiple locations, etc.
    if info_box is not None:
        # Get their name
        page_info['Name'] = info_box.find(class_='heading').get_text().strip()
        page_info['Description'] = info_box.find_next_sibling('p').get_text().strip()
        # Get their details
        # get all dt/dd pairs. This uses list comprehension to create list of text for each element
        # It ends up being value, pairs... 'Race': 'Human', 'Level': '11'...
        details = dict(zip([k.get_text().strip() for k in info_box.find_all('dt')],
                           [v.get_text().strip() for v in info_box.find_all('dd')]))
        for k, v in details.items():
            # TODO: Some keys have multiple values (location). This should be broken out somehow.
            page_info[k] = v

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

    # Pull the pages from a category we want to scrape
    pages = get_category_pages(root_path, category)

    # Get some info form the pages (this is pretty raw data that needs further parsing)
    page_indecies = [2, 3, 71]
    page_details = get_data_from_pages(pages[x] for x in page_indecies)

    # Parse the infobox

    # Parse section X

    # Parse section Y... etc.

    # page_details = get_data_from_pages(pages)
    df = pd.DataFrame(page_details)

    # print("saving to file: /test_file.csv")
    df.to_csv('test_file.csv', index = False, header = True)
    print(df)
    # print(df.Description[2])
    # print(df.TOC[2])

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