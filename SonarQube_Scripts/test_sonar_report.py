import os
import sys
import subprocess
import requests

shipment = sys.argv[1]

#Function to check the branch
def check_branch(projects,journey,branch):
	for project in projects:
		headers = {
			'authority': 'sonarqube.lmera.ericsson.se',
			'accept': 'application/json',
			'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36',
			'x-xsrf-token': 'bqkk43b4oq0r5tgnqog29qdjee',
			'sec-fetch-site': 'same-origin',
			'sec-fetch-mode': 'cors',
			'sec-fetch-dest': 'empty',
			'referer': 'https://sonarqube.lmera.ericsson.se/dashboard?id=com.ericsson.oss.eniq.'+journey+'%3A'+project,
			'accept-language': 'en-US,en;q=0.9',
			'cookie': '_ga=GA1.2.2146927517.1608016603; _fbp=fb.1.1608016603445.191654112; _rdt_uuid=1608016603393.9773df9d-9a68-43c0-8180-84d2ef31231a; XSRF-TOKEN=bqkk43b4oq0r5tgnqog29qdjee; JWT-SESSION=eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJBWGhKb2FVM0ZXSXlNMlp1NDQ0WCIsInN1YiI6ImVzamthZG0xMDAiLCJpYXQiOjE2MTYxNDMwMzMsImV4cCI6MTYxNjQwMzIxMiwibGFzdFJlZnJlc2hUaW1lIjoxNjE2MTQzMDMzNjU1LCJ4c3JmVG9rZW4iOiJicWtrNDNiNG9xMHI1dGducW9nMjlxZGplZSJ9.ZwVgQ8hqyBil4md0Mn54uEd2nJVcUnJWJKdmqI4EG2I',
			}

		response = requests.get('https://sonarqube.lmera.ericsson.se/api/project_branches/list?project=com.ericsson.oss.eniq.'+journey+'%3A'+project, headers=headers, auth=('113e5fae4d562c6b79bca47a56870206c2cff446', ''))
		job_contents = response.content
		job = job_contents.split("}]")
		f = 0
		for line in job:
			if("release-"+branch in line):
				yes_branch.append(project)
				final_dict[project] = branch
				f = 1
				break
		if(f == 0):
			no_branch.append(project)
	return(len(no_branch))

#Function to create the table	
def create_table(projects,journey,journey_table_name):
	html_table = "sonar.html";	
	global f1
	HTMLT = open (html_table , 'a')
	if(f1 != 1):	
		HTMLT.write("<center><table border=\"3\" style=\"width:100\">\n")
		HTMLT.write("<tr bgcolor=\"#98AFC7\">\n<th>Journey</th>\n<th>MicroServices</th>\n<th>Branch</th>\n<th>Coverage</th>\n<th>Duplications</th>\n<th>Bugs</th>\n<th>Vulnerabilities</th>\n<th>Code Smells</th>\n</tr>\n")
		f1 = 1
	HTMLT.write("<tr align=\"center\">\n<td rowspan='"+str(len(projects))+"'>"+journey_table_name+"</td>\n")
	HTMLT.close()
	flag = 0
	for project, branch in projects.items():
		print("Gathering the information of "+project)
		headers = {
			'authority': 'sonarqube.lmera.ericsson.se',
			'accept': 'application/json',
			'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36',
			'x-xsrf-token': 'bqkk43b4oq0r5tgnqog29qdjee',
			'sec-fetch-site': 'same-origin',
			'sec-fetch-mode': 'cors',
			'sec-fetch-dest': 'empty',
			'referer': 'https://sonarqube.lmera.ericsson.se/dashboard?branch=release-'+branch+'&id=com.ericsson.oss.eniq.'+journey+'%3A'+project,
			'accept-language': 'en-US,en;q=0.9',
			'cookie': '_ga=GA1.2.2146927517.1608016603; _fbp=fb.1.1608016603445.191654112; _rdt_uuid=1608016603393.9773df9d-9a68-43c0-8180-84d2ef31231a; XSRF-TOKEN=bqkk43b4oq0r5tgnqog29qdjee; JWT-SESSION=eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJBWGhKb2FVM0ZXSXlNMlp1NDQ0WCIsInN1YiI6ImVzamthZG0xMDAiLCJpYXQiOjE2MTYxNDMwMzMsImV4cCI6MTYxNjQwMzIxMiwibGFzdFJlZnJlc2hUaW1lIjoxNjE2MTQzMDMzNjU1LCJ4c3JmVG9rZW4iOiJicWtrNDNiNG9xMHI1dGducW9nMjlxZGplZSJ9.ZwVgQ8hqyBil4md0Mn54uEd2nJVcUnJWJKdmqI4EG2I',
		}

		params = (
			('branch', 'release-'+branch),
			('component', 'com.ericsson.oss.eniq.'+journey+':'+project),
			('metrics', 'bugs,vulnerabilities,sqale_index,duplicated_lines_density,ncloc,coverage,code_smells'),
			('ps', '1000'),
		)

		response = requests.get('https://sonarqube.lmera.ericsson.se/api/measures/search_history', headers=headers, params=params, auth=('113e5fae4d562c6b79bca47a56870206c2cff446', ''))
		job_contents = response.content
		job = job_contents.split("}]")
	
		status = {}

		for line in job:
			if '"metric":"vulnerabilities"' in line:
				length = len(line.split(":")) - 1
				vulnerability = (line.split(":")[length]).strip('""')
				if(int(float(vulnerability))>0):
					status['vulnerability'] = 'red'
				else:
					status['vulnerability'] = 'white'
			if '"metric":"coverage"' in line:
				length = len(line.split(":")) - 1
				coverage = (line.split(":")[length]).strip('""')
				if(int(float(coverage))<80):
					status['coverage'] = 'red'
				else:
					status['coverage'] = 'white'
			if '"metric":"duplicated_lines_density"' in line:
				length = len(line.split(":")) - 1
				duplicated = (line.split(":")[length]).strip('""')
				if(int(float(duplicated))>0):
					status['duplicated'] = 'red'
				else:
					status['duplicated'] = 'white'
			if '"metric":"bugs"' in line:
				length = len(line.split(":")) - 1
				bug = (line.split(":")[length]).strip('""')
				if(int(float(bug))>0):
					status['bug'] = 'red'
				else:
					status['bug'] = 'white'
			if '"metric":"code_smells"' in line:
				length = len(line.split(":")) - 1
				code_smell = (line.split(":")[length]).strip('""')
				if(int(float(code_smell))>0):
					status['code_smell'] = 'red'
				else:
					status['code_smell'] = 'white'
		
		html_table = "sonar.html";
		HTMLT = open (html_table , 'a')
		url = "https://sonarqube.lmera.ericsson.se/dashboard?branch=release-"+branch+"&id=com.ericsson.oss.eniq."+journey+"%3A"+project
		if(flag != 1):
			HTMLT.write("<td style='text-align:center;'><b><a href=" + url +">"+project+"</a></b></td style='text-align:center;'>\n<td>"+branch+"</td>\n<td style='text-align:center;' bgcolor= '"+status['coverage']+"'>"+coverage+"%</td>\n<td style='text-align:center;' bgcolor= '"+status['duplicated']+"'>"+duplicated+"%</td>\n<td style='text-align:center;' bgcolor= '"+status['bug']+"'>"+bug+"</td>\n<td style='text-align:center;' bgcolor= '"+status['vulnerability']+"'>"+vulnerability+"</td>\n<td style='text-align:center;' bgcolor= '"+status['code_smell']+"'>"+code_smell+"</td>\n</tr>")
			flag = 1
		else:
			HTMLT.write("<td style='text-align:center;'><b><a href=" + url +">"+project+"</a></b></td>\n<td style='text-align:center;'>"+branch+"</td>\n<td style='text-align:center;' bgcolor= '"+status['coverage']+"'>"+coverage+"%</td>\n<td style='text-align:center;' bgcolor= '"+status['duplicated']+"'>"+duplicated+"%</td>\n<td style='text-align:center;' bgcolor= '"+status['bug']+"'>"+bug+"</td>\n<td style='text-align:center;' bgcolor= '"+status['vulnerability']+"'>"+vulnerability+"</td>\n<td style='text-align:center;' bgcolor= '"+status['code_smell']+"'>"+code_smell+"</td>\n</tr>")
		HTMLT.close()
		print("Information is gathered for "+project)

#Function to gather the data of those projects for which the branch doesn't exist
def no_status(projects,journey,journey_table_name):
	global f2
	HTMLT = open (html_table1 , 'a')
	if(f2 != 1):	
		HTMLT.write("<center><h2>No Analysis found for "+shipment+" branch in below projects</h2></center>")
		f2 = 1
	flag = 0
	for project in projects:
		if(flag != 1):
			HTMLT.write("<center><b>"+journey_table_name+"</b></center>\n")
			flag = 1
		url = "https://sonarqube.lmera.ericsson.se/dashboard?id=com.ericsson.oss.eniq."+journey+"%3A"+project
		HTMLT.write("<center><b><a href=" + url +">"+project+"</a></b></center>\n")
		print(shipment+" branch doesn't exist in SonarQube for "+project)
	HTMLT.close()
	
		
data_ingress = ['eric-oss-eniq-parser-ebs','eric-oss-eniq-parser-3gpp32435','eric-oss-eniq-parser-ascii','eric-oss-eniq-parser-ct','eric-oss-eniq-parser-mdc','eric-oss-eniq-loadfile-builder','eric-oss-eniq-parser-common','eric-oss-eniq-loader-sapiq']
managment_system = ['eric-oss-eniq-ui-install-sw','eric-oss-eniq-system-monitoring','eric-oss-eniq-install-sw','eric-oss-eniq-ui-system-monitoring']

f1 = 0
f2 = 0

html_table = "sonar.html";
html_table1 = "temp.html";

HTMLT = open (html_table , 'w')
HTMLT.write("<html>\n<head><center><h1>cEniq SonarQube Analysis Report</h1></center></head>\n<body>")
HTMLT.close()

HTMLT = open (html_table1 , 'w')
HTMLT.close()

fp1 = open("branch.txt",'r')
l1 = fp1.readlines()
fp1.close()

length = len(l1)

###For Data Ingresss
no_branch = []
yes_branch = []

no_branch1 = data_ingress
final_dict = {}
for i in range(length):		
	no_branch = []
	yes_branch = []

	l = check_branch(no_branch1,"dataingress",l1[i].strip())

	no_branch1 = []
	no_branch1 = no_branch

create_table(final_dict,"dataingress","DataIngress")

###For Management System
no_branch = []
yes_branch = []

no_branch1 = managment_system
final_dict = {}
for i in range(length):		
	no_branch = []
	yes_branch = []

	l = check_branch(no_branch1,"mgmtsystem",l1[i].strip())

	no_branch1 = []
	no_branch1 = no_branch

create_table(final_dict,"mgmtsystem","ManagmentSystem")

HTMLT = open (html_table1 , 'r')
contents = HTMLT.readlines()
HTMLT.close()

HTMLT = open (html_table , 'a')
if(f1 != 0):
	HTMLT.write("</center></table>\n")
HTMLT.writelines(contents)
HTMLT.close()

HTMLT = open (html_table , 'a')

os.system("rm -rf "+html_table1)




