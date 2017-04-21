# jss-static-groups
Python scripts to manipulate JSS static computer groups (add computer, move software to another computer, etc.)

**Setup:**
* All scripts use the [requests Python library](http://docs.python-requests.org/en/master/). Please refere to the [Installation](http://docs.python-requests.org/en/master/user/install/) chapter on the Requests homepage.
* All scripts read JSS connection settings from a JSON file: ~/Library/Preferences/com.github.mvc2c.plist
    
    dict with connection settings:
    
    {'jss_pass':'yourPassword', 'jss_user':'yourUser', 'jss_url':'https://yourJSSUrl:8443', 'jss_verify':0, 'jss_warn':1}
       
       if your JSS has a self signed certificate set jsss_verify to 0 and jss_warn to 1
       jss_url must be the full url including https:// and port i.e. :8443
       
* All scripts were written and tested with a self hosted JSS with self signed certificate. I can't tell if the scripts will work with a JAMF hosted JSS or a JSS with official certificate when verify and warnings should be enabled.

**mvc2c.py**
A litte utility to "move" software from one computer to another computer. To prevent weird results or corruption of the JSS database we only use assignments to static computer groups.
The script fetches all computergroup memberships of the source computer and matches those to static computergroups in JSS. The destination computer is then added to all matching static computergroups.

    usage: mvc2c.py [-h] [-s SOURCE] [-d DESTINATION]

    optional arguments:

    -h, --help            show this help message and exit
  
    -s SOURCE, --source SOURCE
  
                        Optional: Name of a source computer to read computergroup
                        memberships.
                        
    -d DESTINATION, --destination DESTINATION
  
                        Optional: Name of a destination computer that will be
                        assigned to matching static computergroups.
                        
 If no arguments are provided the script prompts for source and destination computer.
