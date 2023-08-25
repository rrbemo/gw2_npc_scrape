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
    # I've tried to use .children here and it did not work properly
    for tag in soup.find(id='mw-content-text').find('div', class_='mw-parser-output').find_all(recursive=False):
        # print(tag)
        # Ignore navigable strings
        if isinstance(tag, bs.element.NavigableString):
            continue
        if tag.name == 'h2':
            break
        # Skip the infobox
        if tag.name == 'div':
            if 'class' in tag.attrs.keys() and 'infobox' in tag['class']:
                # This is the infobox (multiple infoboxes will mess this up)
                page_info['InfoBox_RAW'] = tag # Set the TOC to something else
            elif 'id' in tag.attrs.keys() and 'toc' in tag['id']:
                # This is the toc, let's store that for later parsing
                page_info['TOC_RAW'] = tag
            # Else, just add it to the list of description items
            else:
                if 'Description_RAW' in page_info.keys():
                    page_info['Description_RAW'].append(tag)
                else:
                    page_info['Description_RAW'] = tag

        # Else we will consider this as part of the description and add it.
        else:
            if 'Description_RAW' in page_info.keys():
                page_info['Description_RAW'].append(tag)
            else:
                page_info['Description_RAW'] = tag

    # Parse the remainder of the page based on the TOC.
    sections = {}
    if 'TOC_RAW' in page_info.keys():
        # Use the TOC to determine which sections we need to parse
        for tag in page_info['TOC_RAW'].find('ul').children:
            if isinstance(tag, bs.element.NavigableString):
                continue
            if tag.name == 'li' and 'class' in tag.attrs.keys() and 'toclevel-1' in tag['class']:
                sections[tag.find('a')['href'].replace("#", "")] = tag.find('span', class_='toctext').get_text().strip()
    else:
        # There is no TOC and we should loop through each h2 heading to determine what to do
        for tag in soup.find('div', class_='mw-parser-output').children:
            if isinstance(tag, bs.element.NavigableString):
                continue
            #print(tag)
            if tag.name == 'h2':
                headline = tag.find_next('span', class_='mw-headline')
                if 'id' in headline.attrs.keys():
                    sections[headline['id']] = headline.get_text().strip()

    # Make a column for each section found (TOC or by h2 tag)
    for k in sections.keys():
        section_raw = k + '_RAW'
        # Go to the beginning of that section
        for tag in soup.find(id=k).parent.find_next_siblings():
            if isinstance(tag, bs.element.NavigableString):
                if section_raw in page_info.keys():
                    page_info[section_raw].append(tag)
                else:
                    page_info[section_raw] = tag
            elif tag.name == 'h2':
                break
            else:
                # Remove "edit" spans
                for edit_tag in tag.find_all('span', class_='mw-editsection'):
                    edit_tag.decompose()
                if section_raw in page_info.keys():
                    page_info[section_raw].append(tag)
                else:
                    page_info[section_raw] = tag

    # parse infobox
    if 'InfoBox_RAW' in page_info.keys():
        ib = page_info['InfoBox_RAW']
        page_info['IB_Name'] = ib.find('p', class_='heading').get_text().strip()
        details = dict(zip([k.get_text().strip().replace(" ", "_") for k in ib.find_all('dt')],
                           [v for v in ib.find_all('dd')]))
        for k, v in details.items():
            # TODO: Some keys have multiple values (location). This should be broken out somehow.
            child_count = 0
            multiples = {}
            for tag in v.children:
                if isinstance(tag, bs.element.NavigableString):
                    continue
                if tag.name not in ('br', 'small'):
                    if tag.name == 'a':
                        multiples[child_count] = tag.get_text().strip()
                    #print(tag)
                    child_count += 1
            #print(k + ": " + str(child_count))
            if child_count > 1:
                page_info['IB_' + k] = multiples
            else:
                page_info['IB_' + k] = v.get_text().strip()
        del page_info['InfoBox_RAW']

    # Parse description data
    if 'Description_RAW' in page_info.keys():
        desc_data = page_info['Description_RAW']
        for tag in desc_data.find_all(recursive=False):
            if isinstance(tag, bs.element.NavigableString):
                if 'Description' in page_info.keys():
                    page_info['Description'] += tag
                else:
                    page_info['Description'] = tag
            elif tag.name == 'blockquote':
                bq = tag.get_text().strip()
                if 'Description_Quote_CLEAN' in page_info.keys():
                    page_info['Description_Quote'] += '\n' + bq
                else:
                    page_info['Description_Quote'] = bq
            else: #if tag.name == 'p':
                desc_text = tag.get_text().strip()
                if 'Description_CLEAN' in page_info.keys():
                    page_info['Description'] += '\n' + desc_text
                else:
                    page_info['Description'] = desc_text
        # Lastly, remove the RAW piece here so we don't run it again below:
        del page_info['Description_RAW']

    # Raw sections
    raw_sections = [x for x in page_info.keys() if x.endswith('_RAW')]

    # Parse description data
    for section in raw_sections:
        section_cleaned = section.replace('_RAW', '')
        data = page_info[section]
        for tag in data:
            if isinstance(tag, bs.element.NavigableString):
                if section_cleaned in page_info.keys():
                    page_info[section_cleaned] += tag
                else:
                    page_info[section_cleaned] = tag
            elif tag.name == 'div':
                continue  # skip divs for now
            else:  # if tag.name == 'p':
                data_text = tag.get_text().strip()
                if section_cleaned in page_info.keys():
                    page_info[section_cleaned] += '\n' + data_text
                else:
                    page_info[section_cleaned] = data_text
        # print(section_cleaned)
        # print(page_info[section_cleaned])
        # Remove the raw form from the dictionary
        del page_info[section]



    # Parse other sections

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
    # Remove the "Story Characters" page if it is in the list of URLS. This is a circular page and creates clutter.
    page_urls.remove('https://wiki.guildwars2.com/wiki/Story_characters')
    for page_url in page_urls:
        page_infos.append(get_page_data(page_url))

    return(page_infos)

def main(root_path, category):

    # Pull the pages from a category we want to scrape
    pages = get_category_pages(root_path, category)

    # Get some info form the pages (this is pretty raw data that needs further parsing)
    # page_indecies = [0, 1, 2, 3]
    # less_pages = [pages[x] for x in page_indecies]
    # page_details = get_data_from_pages(less_pages)
    page_details = get_data_from_pages(pages)
    df = pd.DataFrame(page_details)

    # print("saving to file: /test_file.csv")
    df.to_csv('test_file.csv', index=False, header=True)
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