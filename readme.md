This script was written by Andrew Lee (andrewlee2023@u.northwestern.edu) in December 2021.

# Summary and Purpose

This script can access the ICSD API in a programmatic way to download cif files given a query.

**WARNING: This script downloads both theoretical AND experimental structures!**

To filter out theoretical structures, you must first download them separately using the web client, which has the option to select only theoretical compounds. Then, you can remove these theoretical files from those retrieved through this script.


# How to use

1. Initialize icsd_swagger class with the following inputs
    - loginid: string of the login id (ask Andrew for this)
    - password: string of the login password


2. Call the login function to log in with the specified credentials.

3. Call the simple_search or expert_search functions with inputs:
    - query_text: string of query text as defined in the ICSD website
        - simple search query syntax can be found [here](https://icsd.fiz-karlsruhe.de/resources/content/help/ICSD_Help.pdf#page=9)
        - expert search query syntax can be found [here](https://icsd.fiz-karlsruhe.de/search/expertSearch.xhtml)

4. Or you can supply your own array of ICSD collection codes via the custom_coll_codes function with the input:
    - coll_codes: array of collection codes (strings of ints) to download
    - !!UPDATE!!: this code is NOT the same as the ICSD collection codes on the web interface. This code appears to be numbered separately for just the API system...

5. Call the download_cifs function to download the relevant cifs that satisfy the query conditions

6. (optional) Call the unzip_downloads function to unzip all downloaded cifs into a destination specified in the function input:
    - destination: string of folder you want to unzip all cifs into
        
7. Call the logout function (**IMPORTANT!**)


# Example

```
from icsd_query import *

icsd = icsd_swagger(loginid = 'your_login_id_here',password = 'your_login_password_here')

icsd.login()

icsd.simple_search(query_text = 'NaCl')

icsd.download()

icsd.logout()

```
