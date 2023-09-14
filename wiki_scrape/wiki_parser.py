import pandas as pd
import urllib.parse
import bs4 as bs

# Parse a page
def parse_raw_section(raw_section_data, section_name, category):
    # Determine what to parse and parse it
    section_data = {}
    # If this section is a known section/category combination, scrape it a specific way,
    if section_name == 'InfoBox_RAW':
        # This is an infobox to parse
        return(parse_infobox(raw_section_data, category))
    elif section_name == 'Description_RAW':
        # This is a description section and needs some attention
        return(parse_description(raw_section_data, category))
    # else, scrape it generically
    else:
        #Parse description data
        section_name_cleaned = section_name.replace('_RAW', '')

        for tag in raw_section_data:
            if isinstance(tag, bs.element.NavigableString):
                if section_name_cleaned in section_data.keys():
                    section_data[section_name_cleaned] += tag
                else:
                    section_data[section_name_cleaned] = tag
            elif tag.name == 'div':
                continue  # skip divs for now
            else:  # if tag.name == 'p':
                data_text = tag.get_text().strip()
                if section_name_cleaned in section_data.keys():
                    section_data[section_name_cleaned] += '\n' + data_text
                else:
                    section_data[section_name_cleaned] = data_text
    return(section_data)

def parse_infobox(raw_section_data, category):
    # If there is some special category to consider...

    # Else, parse this as a standard parse of an infobox
    section_data = {}
    # parse infobox
    heading = raw_section_data.find('p', class_='heading')
    if heading:
        section_data['IB_Name'] = heading.get_text().strip()
    details = dict(zip([k.get_text().strip().replace(" ", "_") for k in raw_section_data.find_all('dt')],
                       [v for v in raw_section_data.find_all('dd')]))
    # Loop through each dt:dd pair.
    for k, v in details.items():
        # This is an attempt at pulling out multiples, but some other information is lost.
        # For now though, it seems like just putting all the text in and splitting it later on might be best.
        tag_count = 0
        item_group_count = 0
        multiples = []
        item_group = ""
        for tag in v.find_all(recursive=False):
            is_tag_ns = isinstance(tag, bs.element.NavigableString)
            # Skip if this is just a newline tag
            if not is_tag_ns and tag.name == 'br':
                continue
            tag_count += 1
            # If this is the first item, treat it a little different.
            if tag_count == 1:
                if is_tag_ns:
                    item_group = tag.strip()
                else:
                    item_group = tag.get_text().strip()
                item_group_count += 1
            # Else, handle it
            else:
                if is_tag_ns:
                    item_group += tag.strip()
                elif tag.name == 'small':
                    item_group += tag.get_text().strip()
                else:
                    multiples.append(item_group)
                    item_group = tag.get_text().strip()
                    item_group_count += 1
        # Add the last item group to the multiples
        multiples.append(item_group)
        # This handles if there are no children
        if item_group_count > 0:
            section_data['IB_' + k] = multiples
        else:
            section_data['IB_' + k] = [v.string.strip()]

    return(section_data)

def parse_description(raw_section_data, category):
    section_data = {}
    # Parse description data
    for tag in raw_section_data.find_all(recursive=False):
        if isinstance(tag, bs.element.NavigableString):
            if 'Description' in section_data.keys():
                section_data['Description'] += tag
            else:
                section_data['Description'] = tag
        elif tag.name == 'blockquote':
            bq = tag.get_text().strip()
            if 'Description_Quote_CLEAN' in section_data.keys():
                section_data['Description_Quote'] += '\n' + bq
            else:
                section_data['Description_Quote'] = bq
        else: #if tag.name == 'p':
            desc_text = tag.get_text().strip()
            if 'Description_CLEAN' in section_data.keys():
                section_data['Description'] += '\n' + desc_text
            else:
                section_data['Description'] = desc_text

    return(section_data)




# Parse other sections
