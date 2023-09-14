# Inspiration from https://www.kaggle.com/datasets/muhajipra/people-of-skyrim
import bs4 as bs
import urllib.request
import pandas as pd
import urllib.parse
from wiki_parser import *

def get_category_pages(root_path, category, get_all = True):
    category_path = root_path + '/wiki/Category:' + category
    all_pages = []
    url_pages = get_pages_for_url(root_path, category_path)

    # A "page" here refers to a character page which is displayed. 200 is the max shown per request.
    # Loop to get more pages while the max number of pages is hit for each query
    while len(url_pages) >= 200 and get_all:
        # Get the last page (url) and strip out the name of the page to start from there next time
        # I pop this off the list so that we don't get duplicates when we append.
        last_url = url_pages.pop(-1)
        start_from = urllib.parse.quote(last_url.split('/')[-1])

        # Append the last set of pages found do the current list.
        all_pages = all_pages + url_pages

        # Get the next set of pages starting from the last page found last url from the last request.
        url_pages = get_pages_for_url(root_path, root_path + '/?title=Category:' + category + '&pagefrom=' + start_from)

    # Make sure the last url_page pull is added (or set to) all_pages (outside the loop)
    all_pages = all_pages + url_pages

    return(all_pages)

def get_pages_for_url(root_path, this_url):
    # This will return a list of pages for a given URL
    sauce = urllib.request.urlopen(this_url).read()
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

    return(page_info)

# Get all pages data (one page at a time)
def get_data_from_pages(page_urls):
    page_infos = []
    # Remove the "Story Characters" page if it is in the list of URLS. This is a circular page and creates clutter.
    sc_url = ['https://wiki.guildwars2.com/wiki/Story_characters',
              'https://wiki.guildwars2.com/wiki/Legendary_weapon',
              'https://wiki.guildwars2.com/wiki/Legendary_weapon/table']
    for a_url in sc_url:
        while a_url in page_urls:
            print("removing '" + a_url + "'")
            page_urls.remove(a_url)

    # Scrape the data for each page.
    for page_url in page_urls:
        page_infos.append(get_page_data(page_url))

    return(page_infos)

def get_links_from_pages(root_path, page_urls):
    page_links = []
    # Remove any circular references related to the category being searched.
    sc_url = ['https://wiki.guildwars2.com/wiki/Story_characters',
              'https://wiki.guildwars2.com/wiki/Legendary_weapon',
              'https://wiki.guildwars2.com/wiki/Legendary_weapon/table']
    for a_url in sc_url:
        while a_url in page_urls:
            print("removing '" + a_url + "'")
            page_urls.remove(a_url)

    # Scrape the data for each page.
    print(page_urls)
    for page_url in page_urls:
        page_links += get_page_links(root_path, page_url)

    return(page_links)

# Get all links back to the same domain
def get_page_links(root_path, page_url):
    # Connections should be a list of dictionary items (connections) with two keys each, "to" and "from".
    # "to" should be where the link goes to and "from" should be this page url.
    connections = []
    sauce = urllib.request.urlopen(page_url).read()
    soup = bs.BeautifulSoup(sauce, "lxml")
    # Find all anchors
    all_anchors = soup.find(id='mw-content-text').find('div', class_='mw-parser-output').find_all('a')

    for anchor in all_anchors:
        relationship = None
        if 'href' in anchor.attrs.keys():
            this_href = anchor['href']
            if this_href.startswith('//'):
                if 'action=edit' not in this_href:
                    # This is an external link. We may want to do something different with these links
                    relationship = {'to': this_href,
                                    'from': page_url}
                else:
                    continue  # Skip this because it is an edit link
            elif this_href.startswith('#'):
                # This is a link to this page, so ignore it
                continue
            elif this_href.startswith('/'):
                if 'action=edit' not in this_href:
                    # This should be a link to this same root wiki (primarily what we are looking for
                    relationship = {'to': root_path + this_href,
                                    'from': page_url}
                else:
                    continue  # Skip this because it is an edit link
            else:
                # Else we will just save it for now.
                relationship = {'to': this_href,
                                'from': page_url}
        if relationship:
            connections.append(relationship)

    return connections

def scrape_html(root_path, category):
    # Pull the pages from a category we want to scrape
    pages = get_category_pages(root_path, category, get_all=False) # Only get the first page for testing
    #pages = get_category_pages(root_path, category)
    print(pages)
    print(len(pages))
    # Get some info form the pages (this is pretty raw data that needs further parsing)
    # page_indecies = [0, 1, 2, 3, 71]
    # less_pages = [pages[x] for x in page_indecies]
    # page_details = get_data_from_pages(less_pages)

    page_details = get_data_from_pages(pages)
    df = pd.DataFrame(page_details)
    #df.to_csv(category + '_text.csv', index=False, header=True)
    df.to_csv(category + '_raw.csv', index=False, header=True)
    print("saving to file: /" + category + "_text.csv")

def scrape_text(root_path, category):

    # Pull the pages from a category we want to scrape
    pages = get_category_pages(root_path, category, get_all=False) # Only get the first page for testing
    #pages = get_category_pages(root_path, category)
    print(pages)
    print(len(pages))
    # Get some info form the pages (this is pretty raw data that needs further parsing)
    # page_indecies = [0, 1, 2, 3, 71]
    # less_pages = [pages[x] for x in page_indecies]
    # page_details = get_data_from_pages(less_pages)

    # This is a list of all pages and their raw details
    page_details_raw = get_data_from_pages(pages)
    page_details = []
    # Loop each page
    for a_page in page_details_raw:
        #print(a_page.keys())
        raw_sections = [x for x in a_page.keys() if x.endswith('_RAW')]
        # Pre-load the dictionary with all non-raw sections
        a_page_clean = {k:v for (k,v) in a_page.items() if not k.endswith('_RAW')}
        # Clean all sections for page
        for section in raw_sections:
            # Add sections back for each raw section. A single section may come back as multiple
            temp_dict = parse_raw_section(a_page[section], section, category)
            a_page_clean.update(temp_dict) # merge the two dictionaries together (could also use | in 3.9+)
        page_details.append(a_page_clean)

    df = pd.DataFrame(page_details)
    #df.to_csv(category + '_text.csv', index=False, header=True)
    df.to_csv(category + '_text.csv', index=False, header=True)
    print("saving to file: /" + category + "_text.csv")
    # print(df)
    # print(df['IB_Location'])

def scrape_links(root_path, category):
    # Pull the pages from a category we want to scrape
    # pages = get_category_pages(root_path, category, get_all=False)  # Only get the first page for testing
    pages = get_category_pages(root_path, category)
    # print(pages)
    # print(len(pages))
    # Get some info form the pages (this is pretty raw data that needs further parsing)
    # page_indecies = [0, 1, 2, 3, 71]
    # less_pages = [pages[x] for x in page_indecies]
    # page_links = get_links_from_pages(root_path, less_pages)

    page_links = get_links_from_pages(root_path, pages)

    df = pd.DataFrame(page_links)
    df.to_csv(category + '_links.csv', index=False, header=True)
    print("saving to file: /" + category + "_links.csv")

if __name__ == "__main__":
   # main('https://wiki.guildwars2.com', "story_characters")
    # scrape_text('https://wiki.guildwars2.com', 'Normal_NPCs')
    # scrape_links('https://wiki.guildwars2.com', 'Normal_NPCs')
    # scrape_links('https://wiki.guildwars2.com', 'Veteran_NPCs')
    # scrape_links('https://wiki.guildwars2.com', 'Elite_NPCs')
    #scrape_links('https://wiki.guildwars2.com', 'Legendary_NPCs')

    # Test for weapons scraping
    scrape_html('https://wiki.guildwars2.com', 'Legendary_weapons')
    #scrape_text('https://wiki.guildwars2.com', 'Legendary_weapons')

    # Test for weapons api
    #scrape_api('https://wiki.guildwars2.com', 'Legendary_weapons')
    # categories to check:
    # story_characters
    # All "NPCs_by_rank" below
        # Normal_NPCs
        # Veteran_NPCs
        # Elite_NPCs
        # Epic_NPCs
        # Legendary_NPCs
        # Ambient_creatures
        # Merchants

   # It would be nice to have a list of all other linked pages in this wiki