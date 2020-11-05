#Requirments: selenium,chromedriver,pavucontrol
#chromedriver: https://askubuntu.com/questions/870530/how-to-install-geckodriver-in-ubuntu
#pavucontrol guide: https://itectec.com/ubuntu/ubuntu-capturing-only-desktop-audio-with-ffmpeg/
#pydrive guide: https://medium.com/analytics-vidhya/how-to-connect-google-drive-to-python-using-pydrive-9681b2a14f20

import datetime
import time
import subprocess
import selenium
import sqlite3
from shlex import split
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.chrome.options import Options
from os import mkdir,path, listdir, devnull
from operator import attrgetter
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

#SCRIPT PARAMETERS-BEGIN
TEAMS_EMAIL = 'el18XXX@ntua.gr'
NTUA_USERNAME =  'el18XXX'
NTUA_PASSWORD = 'YOUR_PASSWORD_HERE'
IMPLICITLY_WAIT_TIME = 30 #seconds/default = 60
RETRY_TO_JOIN =  30 #seconds/default = 60
REC_FRAMES_PER_SECOND = 10
DATABASE_NAME = "myschedule.db"
MINUTES_BEFORE_LECTURE = 0
MINUTES_AFTER_LECTURE = 10
#SCRIPT PARAMETERS-END

def tupleToLecture(t):
	#takes a tuple as parameter and returns a lecture object
	#lecture infromation fetched from db
	tuple_course = t[0]
	tuple_start_hour = t[-4]
	tuple_start_minute = t[-3]
	tuple_end_hour =  t[-2]
	tupe_end_minute = t[-1]

	tuple_starting_time = timeFormat(tuple_start_hour,tuple_start_minute) #turn time to seconds since epoch format
	tuple_ending_time = timeFormat(tuple_end_hour,tupe_end_minute)

	index_of_course = courses_names_list.index(tuple_course) #courses_names_list is global

	tuple_lecture_platform_attr1 = courses_list[index_of_course][2] #courses_list is global
	tuple_lecture_platform_attr2 = courses_list[index_of_course][3]
	tuple_lecture_no = courses_list[index_of_course][4]

	if courses_list[index_of_course][1] == "Teams" and bool(tuple_lecture_platform_attr2):
		newLecture = teamsLecture(tuple_course,tuple_lecture_no+1,tuple_starting_time,tuple_ending_time,tuple_lecture_platform_attr1,tuple_lecture_platform_attr2)
	elif courses_list[index_of_course][1] == "Teams" and not(bool(tuple_lecture_platform_attr2)):
		newLecture = teamsLecture(tuple_course,tuple_lecture_no+1,tuple_starting_time,tuple_ending_time,tuple_lecture_platform_attr1)#no channel is given
	else:
		newLecture = webexLecture(tuple_course,tuple_lecture_no+1,tuple_starting_time,tuple_ending_time,tuple_lecture_platform_attr1)
	return newLecture	


def setupChromeOptions():
	chrome_options = Options()
	chrome_options.add_argument("--disable-infobars")
	chrome_options.add_argument("start-maximized")
	chrome_options.add_argument("--disable-extensions")
	# Pass the argument 1 to allow and 2 to block
	chrome_options.add_experimental_option("prefs", { \
	    "profile.default_content_setting_values.media_stream_mic": 2, 
	    "profile.default_content_setting_values.media_stream_camera": 2,
	    "profile.default_content_setting_values.geolocation": 2, 
	    "profile.default_content_setting_values.notifications": 2 
	  })
	return chrome_options


def createDirectory():
	try:
		mkdir('recorded_lectures/' + datetime.date.today().isoformat()) #creates directory to save today's recordings
	except Exception as e:
		print("mkdir: Directory already exists, no need to create it.")	


def timeFormat(hour_int, minute_int):
	#gets hour and minute and returns seconds since epoch for today
	d = datetime.datetime.now().date()
	yday = d.toordinal() - datetime.date(d.year, 1, 1).toordinal() + 1
	time_data = time.struct_time((d.year, d.month, d.day, hour_int, minute_int, 0, d.weekday(), yday, -1))
	result = time.mktime(time_data) #from struct_time to seconds since epoch
	return result	


def os_settings():
	volume_command = split('amixer -D pulse sset Master 100%')
	unmute_command = split('amixer -D pulse sset Master unmute')
	idle_command = split('gsettings set org.gnome.desktop.session idle-delay 0')
	
	volumeProcess = subprocess.Popen(volume_command ,stdout=subprocess.DEVNULL) 
	unmuteProcess = subprocess.Popen(unmute_command ,stdout=subprocess.DEVNULL) 
	idleProcess = subprocess.Popen(idle_command ,stdout=subprocess.DEVNULL)


def uploadToDrive(db_cursor):
	gauth = GoogleAuth()
	gauth.LoadCredentialsFile("credentials.txt")
	google_drive = GoogleDrive(gauth)

	parent_dir = 'recorded_lectures/' + datetime.date.today().isoformat()
	lectrures_to_upload = listdir(parent_dir)

	for recording_title in lectrures_to_upload:
		drive_folder_name = recording_title.split(" -")[0]
		try:
			drive_folder = google_drive.ListFile({'q': "title = '{}' and trashed=false".format(drive_folder_name)}).GetList()[0] 
		except Exception as e:
			drive_folder = google_drive.ListFile({'q': "title = 'misc' and trashed=false"}).GetList()[0]
		drive_file = google_drive.CreateFile({'title': recording_title, 'parents': [{'id': drive_folder['id']}]})
		print("Uploading {}".format(recording_title))
		drive_file.SetContentFile(parent_dir + '/' + recording_title)		
		drive_file.Upload()	
		print("Uploaded {}".format(recording_title))
		updateCourseLectureNo(drive_folder_name,db_cursor)


def updateCourseLectureNo(folder_name,db_cursor):
	db_cursor.execute("SELECT number_of_lectures FROM courses_db WHERE course_name = '{}'".format(folder_name));
	new_no_of_lectures = db_cursor.fetchone()[0] + 1
	db_cursor.execute("UPDATE courses_db SET number_of_lectures = {} WHERE course_name = '{}'".format(new_no_of_lectures,folder_name))


class  lecture:
	def __init__(self, course, lecture_no, startingTime, endingTime):  
		self.course = course
		self.lecture_no = lecture_no #startingTime & endingTime given in seconds since epoch
		self.startingTime = startingTime
		self.endingTime = endingTime		

	def record(self):
		output_arg = self.recordName()
		ffmpeg_command = "ffmpeg -f x11grab -video_size 1920x1080 -framerate {} -i :0.0 -f pulse -i default -preset ultrafast -crf 18 -pix_fmt yuv420p {}.mp4 -async 1 -vsync 1".format(REC_FRAMES_PER_SECOND,output_arg)
		ffmpeg_args = split(ffmpeg_command) #split from shlex library
		recordingProcess = subprocess.Popen(ffmpeg_args,stdout=subprocess.DEVNULL) 
		time.sleep(self.endingTime + MINUTES_AFTER_LECTURE *60 - time.time())
		recordingProcess.terminate()

	def recordName(self):
		date_iso = datetime.date.today().isoformat()
		date_str = datetime.date.today().strftime("%d-%m-%Y")
		output_directory = "recorded_lectures/{}/".format(date_iso)
		output_name = "{} - Διάλεξη {} ({})".format(self.course, self.lecture_no,date_str)
		if path.exists(output_directory+output_name+'.mp4'):
			i = 1
			while path.exists(output_directory + output_name + '({})'.format(i) + '.mp4'):
				i=i+1;
			output_name = output_name + '({})'.format(i)
		output_argument = output_directory + "'" + output_name+ "'"
		return output_argument

	def inputTextboxByName(self,textbox_name, input_text):
		try:
			self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
			selectedTextbox = self.browser.find_element_by_name(textbox_name)
			selectedTextbox.clear()
			selectedTextbox.send_keys(input_text)
		except Exception as e:
			print("error: inputTextboxByName with selector '{}' failed".format(textbox_name))

	def inputTextboxByParentDiv(self, parent_class, input_text):
		try:
			self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
			selectedTextbox = self.browser.find_element_by_css_selector('[class^="' + parent_class + '"] input[type="text"]')
			selectedTextbox.clear()
			selectedTextbox.send_keys(input_text)
		except Exception as e:
			print("error: inputTextboxByParentDiv with selector '{}' failed".format(parent_class))

	def clickByName(self,element_name):
		try:
			self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
			clickable_element = self.browser.find_element_by_name(element_name)
			clickable_element.click()
		except Exception as e:
			print("error: clickByName with selector '{}' failed".format(element_name))

	def clickByCssSelector(self,css_selector):
		try:
			self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME)
			clickable_element = self.browser.find_element_by_css_selector(css_selector)
			clickable_element.click()
		except Exception as e:
			print("error: clickByCssSelector with selector '{}' failed".format(css_selector))	

	def clickById(self,id_selector):
		try:
			self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
			clickable_element = self.browser.find_element_by_id(id_selector)
			clickable_element.click()
		except Exception as e:
			print("error: clickById with selector '{}' failed".format(id_selector))	


class teamsLecture(lecture):
	def __init__(self, course, lecture_no, startingTime, endingTime,team_title, team_channel = "General"): 
		self.team_title = team_title
		if team_title == 'Αρχιτεκτονική Υπολογιστών (ΚΑΤ-ΠΑΠΑΓ)':
			self.team_channel = 'Διάλεξη {}η'.format(lecture_no)
		elif team_title == 'Βιομηχανική Ηλεκτρονική':
			self.team_channel = '{}ο Μάθημα'.format(lecture_no)
		else:
			self.team_channel = team_channel
		lecture.__init__(self, course, lecture_no,startingTime, endingTime) 

	def showDetails(self):
		print("Course:{} | Platform: Teams  | Lecture_No:{} | Starting time: {} | Ending time: {} | Team: {} | Channel: {}".format(self.course, self.lecture_no, time.ctime(self.startingTime), time.ctime(self.endingTime),self.team_title,self.team_channel))		
	
	def teamsLogin(self):
		self.browser = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options = setupChromeOptions());	#may need change
		self.browser.maximize_window()
		self.browser.get("http://teams.microsoft.com/")
		self.inputTextboxByName("loginfmt", TEAMS_EMAIL)
		self.clickByCssSelector( ".button.primary")
		self.inputTextboxByName("j_username", NTUA_USERNAME)
		self.inputTextboxByName("j_password", NTUA_PASSWORD)
		self.clickByName("donotcache")
		self.clickByName("_shib_idp_revokeConsent")
		self.clickByName("_eventId_proceed")
		self.clickByCssSelector(".button.secondary")
		if (self.browser).current_url != 'https://teams.microsoft.com/_#/school//?ctx=teamsGrid':
			self.browser.get("https://teams.microsoft.com/_#/school//?ctx=teamsGrid")
			self.clickByCssSelector(".use-app-lnk") 
	
	def teamsEnterCourse(self):
		#self.clickByCssSelector('#toast-container button[title="Dismiss"]');
		self.clickByCssSelector('profile-picture[title*="' + self.team_title + '"]')
		if self.team_title == 'Αρχιτεκτονική Υπολογιστών (ΚΑΤ-ΠΑΠΑΓ)'  or self.team_title == 'Βιομηχανική Ηλεκτρονική':
			self.clickByCssSelector('.school-app-team-channel   .channel-anchor[title*="hidden channel"]')
			self.clickByCssSelector('.channel-list-overflow-channels   .channel-anchor[title*="' + self.team_channel +'"]')
		else:
			self.clickByCssSelector('.school-app-team-channel   .channel-anchor[title*="' + self.team_channel +'"]')
	
	def teamsJoinMeeting(self):
		while (len(self.browser.find_elements_by_css_selector("calling-join-button button")) == 0):
			time.sleep(RETRY_TO_JOIN)
			self.browser.get(self.browser.current_url)
			self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
		self.clickByCssSelector("calling-join-button button");
		self.clickByCssSelector('button[ng-click="getUserMedia.passWithoutMedia()"]');
		self.clickByCssSelector('button[ng-click="ctrl.joinMeeting()"]');
		self.clickById("callingButtons-showMoreBtn")
		self.clickById("full-screen-button")
	
	def exit(self):
		actions = webdriver.ActionChains(self.browser)
		try:
			hangup_element = self.browser.find_element_by_id("hangup-button")
			actions.move_to_element(hangup_element);
			actions.pause(2)
			actions.click(hangup_element)
			actions.perform()
		except Exception as e:
			raise e
		self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
		self.browser.quit()
	
	def join(self):
		self.teamsLogin()
		self.teamsEnterCourse()
		self.teamsJoinMeeting()


class webexLecture(lecture):
	def __init__(self, course, lecture_no, startingTime, endingTime,webex_url): 
		self.webex_url = webex_url
		lecture.__init__(self, course, lecture_no,startingTime, endingTime) 	

	def showDetails(self):
		print("Course:{} | Platform: Webex | Lecture_No:{} | Starting time: {} | Ending time: {}".format(self.course, self.lecture_no, self.startingTime, self.endingTime))	
	
	def join(self):
		self.browser = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options = setupChromeOptions());	#may need change
		self.browser.maximize_window()
		self.browser.get(self.webex_url)
		self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME)
		while (len(self.browser.find_elements_by_css_selector(".el-button.is-disabled")) != 0):
			time.sleep(RETRY_TO_JOIN)
			browser.get(webex_join_url)
			browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
		self.clickById("smartJoinButton")
		self.browser.switch_to.frame(self.browser.find_element_by_id("pbui_iframe"))
		self.inputTextboxByParentDiv("style-name-input","GK")
		self.inputTextboxByParentDiv("style-email-input","lecturesrec@gmail.com")
		self.clickById("guest_next-btn")
		self.clickByCssSelector('[title="Got it"]')
		self.clickById("interstitial_start_btn")
		self.clickByCssSelector('[title="Change audio connection"]')
		self.clickByCssSelector('.style-audio-menu-3RSLi li:nth-child(2)')
		self.clickById("interstitial_start_btn")
		self.clickByCssSelector('[title="Join anyway"]')

	def exit(self):
		self.browser.implicitly_wait(IMPLICITLY_WAIT_TIME) 
		self.browser.quit()	


def main():
	day = datetime.datetime.now().date().weekday()
	day_int =datetime.datetime.now().date().day
	month_int =datetime.datetime.now().date().month

	db_connection = sqlite3.connect(DATABASE_NAME) 
	c = db_connection.cursor();

	c.execute("SELECT * FROM canceled_days WHERE day_of_the_month ='{}' AND month ='{}'".format(day_int,month_int))
	if len(c.fetchall()) != 0:
		print("No lectures today")
		return
	else:
		createDirectory()

	os_settings()	

	global courses_list,courses_names_list
	c.execute("SELECT * FROM courses_db")
	courses_list = c.fetchall()
	courses_list.sort(key=lambda c: c[0])
	courses_names_list = [i[0] for i in courses_list] #(sorted) list containing only the names of the courses

	#SELECT today's lecture from proper table and save them in a list of tuples. Then convert list of tuples to list of lecture objects(for each tuple->lecture object)
	c.execute("SELECT course_name, starting_time_hour, starting_time_minute, ending_time_hour, ending_time_minute FROM scheduled_lectures WHERE day ='{}'".format(day))
	scheduled_lectures_list_temp = c.fetchall()
	c.execute("SELECT course_name, starting_time_hour, starting_time_minute, ending_time_hour, ending_time_minute FROM extra_lectures WHERE day_of_the_month ='{}' AND month ='{}'".format(day_int,month_int))
	extra_lectures_list_temp = c.fetchall()
	c.execute("SELECT course_name, starting_time_hour, starting_time_minute, ending_time_hour, ending_time_minute FROM canceled_lectures WHERE day_of_the_month ='{}' AND month ='{}'".format(day_int,month_int))
	canceled_lectures_list_temp = c.fetchall()
	lectures_to_be_recorded_temp = scheduled_lectures_list_temp + extra_lectures_list_temp
	
	lectures_to_be_recorded = []
	for i in lectures_to_be_recorded_temp:
		if i in canceled_lectures_list_temp:
			continue
		else:
			lectures_to_be_recorded.append(tupleToLecture(i))	
	lectures_to_be_recorded.sort(key=attrgetter('startingTime')) 

	for l in lectures_to_be_recorded:
		l.showDetails()
		if not(l.endingTime < time.time()):
			waitDuration = (l.startingTime - MINUTES_BEFORE_LECTURE *60) - time.time()
			if waitDuration>0:
				time.sleep(waitDuration)
			l.join()
			l.record()
			l.exit()

	uploadToDrive(c)
	db_connection.commit() 
	db_connection.close()

	reset_idle_command = split('gsettings set org.gnome.desktop.session idle-delay 300')
	reset_idleProcess = subprocess.Popen(reset_idle_command ,stdout=subprocess.DEVNULL)
	#shutdown

if __name__ == "__main__":
	main()
