import  sqlite3

db_connection = sqlite3.connect("test.db") #change db name to myschedule.db
c = db_connection.cursor();

c.execute('CREATE TABLE courses_db(course_name text, platform text, platform_attr_1 text, platform_attr_2 text, number_of_lectures integer)')
c.execute('CREATE TABLE scheduled_lectures(course_name text, day integer, starting_time_hour interger, starting_time_minute integer, ending_time_hour integer, ending_time_minute integer)')
c.execute('CREATE TABLE extra_lectures(course_name text, day_of_the_month integer,month integer, starting_time_hour interger, starting_time_minute integer, ending_time_hour integer, ending_time_minute integer)')
c.execute('CREATE TABLE canceled_lectures(course_name text, day_of_the_month integer,month integer, starting_time_hour interger, starting_time_minute integer, ending_time_hour integer, ending_time_minute integer)')
c.execute('CREATE TABLE canceled_days(day_of_the_month integer, month integer)')

db_connection.commit()
db_connection.close()
