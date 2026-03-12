#action parameters
ELEMENT_LOOKUP_TIMEOUT = 3 #timeout for element lookup (from coordinates) in seconds
INNER_SCROLL_OVERLAP = 5 #overlap in pixels between consecutive scrollable element crops
PAGE_SCROLL_OVERLAP = 50 #overlap in pixels between consecutive page crops
SCROLL_CONFIDENCE_THRESHOLD = 40 #minimum confidence score for scrollable element detection
INNER_SCROLL_CONFIDENCE_THRESHOLD = 40 #minimum confidence score for inner scroll detection
WAIT_CONFIDENCE_THRESHOLD = 40 #minimum confidence score for wait detection
POST_ACTION_WAIT_TIME = 1 #wait time after action in seconds
CLICK_DELAY = 100 #delay between pressing mouse button and releasing it in milliseconds
SCROLL_BATCH_SIZE = 5 #number of crops to send at the same time