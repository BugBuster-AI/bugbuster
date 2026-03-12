import os

scroll_sops = [
    {
        "name": "Kaggle mainpage",
        "url": "https://www.kaggle.com/",
        "sop": [
            "Inner scroll the page until 'AI mathematical Olympiad' panel"
        ],
        "expected_fields": [
            {"action_type", "element_type", "scroll_element_name"},
        ],
        "expected_actions": ["INNER_SCROLL"]
    },
    {
        "name": "Amazon",
        "url": "https://www.amazon.com/",
        "sop": [
            "Click on hamburger menu named 'All' on the top left",
            "Inner scroll left navigation menu until 'Customer Service' item",
            "Click on 'Customer Service' item",
            "Scroll down to the currency selection dropdown",
            "Click on currency selection dropdown",
            "Click on currency settings dropdown",
            "Inner scroll currency settings dropdown to 'Swedish krona' option",
            "Click on 'Swedish krona' option",
            "Click on 'Save changes' button"
        ],
        "expected_fields": [
            {"action_type", "element_type", "element_name", "positional_description"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name"},
        ],
        "expected_actions": ["CLICK", "INNER_SCROLL", "CLICK", "SCROLL", "CLICK", "CLICK", "INNER_SCROLL", "CLICK", "CLICK"]
    },
    {
        "name": "Google account",
        "url": "https://accounts.google.com/",
        "sop": [
            "Click on 'English' language dropdown",
            "Inner scroll language dropdown until 'монгол' option",
            "Click on 'монгол' option"
        ],
        "expected_fields": [
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name"},
        ],
        "expected_actions": ["CLICK", "INNER_SCROLL", "CLICK"]
    },
    {
        "name": "Twitch",
        "url": "https://www.twitch.tv/",
        "sop": [
            "Inner scroll page until 'Music' section",
        ],
        "expected_fields": [
            {"action_type", "element_type", "scroll_element_name"},
        ],
        "expected_actions": ["INNER_SCROLL"]
    },
    {
        "name": "Youtube",
        "url": "https://www.youtube.com/",
        "sop": [
            "Inner scroll left menu to 'Developers' link",
        ],
        "expected_fields": [
            {"action_type", "element_type", "scroll_element_name"},
        ],
        "expected_actions": ["INNER_SCROLL"]
    },
    {
        "name": "Transfermarkt",
        "url": "https://www.transfermarkt.com/",
        "sop": [
            "Click on 'Accept and continue' button in the pop up",
            "Click on 'Country' dropdown",
            "Inner scroll dropdown until 'Germany' option",
            "Click on 'Germany' option",
            "Inner scroll dropdown until 'Oberliga Westfalen' option",
            "Click on 'Oberliga Westfalen' option in the dropdown menu",
            "Inner scroll dropdown until 'VfL Bochum II' option",
            "Click on 'VfL Bochum II' option",
            "Click on double arrow button right next to 'VfL Bochum II' dropdown",
            "Scroll to 'filter by season' dropdown",
            "Click on filter by season dropdown",
            "Inner scroll dropdown until '05/06' option",
            "Click on '05/06' option",
            "Click on 'Show' button"
        ],
        "expected_fields": [
            {"action_type", "element_type", "element_name", "positional_description"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name", "positional_description"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name", "positional_description"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name"},
        ],
        "expected_actions": ["CLICK", "CLICK", "INNER_SCROLL", "CLICK", "INNER_SCROLL", "CLICK", "INNER_SCROLL", "CLICK", "CLICK", "SCROLL", "CLICK", "INNER_SCROLL", "CLICK", "CLICK"]
    },
    {
        "name": "Wikipedia_1",
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "sop": [
            "Click on tools dropdown",
            "Inner scroll dropdown until 'Wiktionary' option",
            "Click on 'Wiktionary'"
        ],
        "expected_fields": [
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_name"},
        ],
        "expected_actions": ["CLICK", "INNER_SCROLL", "CLICK"]
    },
    {
        "name": "Wikipedia_2",
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "sop": [
            "Click on tools dropdown",
            "Click on 'Move to sidebar' button",
            "Inner scroll sidebar until 'Wiktionary' option",
            "Click on 'Wiktionary' option"
        ],
        "expected_fields": [
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "element_name"},
            {"action_type", "element_type", "scroll_element_name"},
            {"action_type", "element_type", "element_name"},
        ],
        "expected_actions": ["CLICK", "CLICK", "INNER_SCROLL", "CLICK"]
    },
    {
        "name": "test_inner_scroll", 
        "url": "file://" + os.getcwd() + "/complex_test.html",
        "sop": [
            "Inner scroll 'Memofield' dropdown until 'line 15' option"
        ],
        "expected_fields": [
            {"action_type", "element_type", "element_name", "scroll_element_name"},
        ],
        "expected_actions": ["INNER_SCROLL"]
    },
    {
        "name": "test_inner_scroll_2",
        "url": "file://" + os.getcwd() + "/complex_test.html",
        "sop": [
            "Inner scroll 'Nested scrollable content' until 'Row 5' option"
        ],
        "expected_fields": [
            {"action_type", "element_name", "scroll_element_name"},
        ],
        "expected_actions": ["INNER_SCROLL"]
    }
]