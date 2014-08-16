# -*- coding: utf-8 -*-

#########################################################################
# @arnav : search for the tag 'To-Do' to see whats to be done. 			#
#########################################################################

import os
import tarfile
import xml.etree.ElementTree as ET
import threading
import datetime
import time
from multiprocessing import Process

def index():
	msg = request.vars['msg']    
	if not msg:
		msg = 'Welcome'
	response.flash = T(msg)
	return dict(login_form=auth.login(),message=T('Hello World'))

def temp():
	return locals()

def autoAssignment():
	form = SQLFORM(db.AutoAssign)
	if form.process().accepted:
		filename = form.vars.upfile	
		response.flash = 'assignment added'
		msg = processFile(filename)
		redirect(URL(r=request,f='index?msg='+msg))
	elif form.errors:
		response.flash = 'upload has errors'
	else:
		response.flash = 'upload the assignment as .xml'
	
	return dict(form=form)

def uploadTarBall():
	req_course = request.vars['course']
	if req_course:
		try:
			course = db(db.Course.id == req_course).select()
			if len(course):
				all_assigns = {}
				course = course[0]
				assigns = db(db.Assign.course == course).select()
				for x in range(len(assigns)):
					all_assigns[assigns[x].id] = assigns[x].name
					db.ImageStack.assign.requires = IS_IN_SET(all_assigns)
					print "all",all_assigns
		except:
			pass
	form = SQLFORM(db.ImageStack)
	if form.process().accepted:
		filename = form.vars.upfile
		course_id = form.vars.course
		course = db(db.Course.id == course_id).select(db.Course.name).first()
		course = course.name
	    #########################################################################################################
#To-Do: # This here should only show assignments under the specific course selected. Lookup - Cascaded dropdowns#
	    #########################################################################################################
		assign_id = form.vars.assign
		print "ass",assign_id
		assign = db(db.Assign.id == assign_id).select(db.Assign.name).first()
		assign = assign.name
		msg = 'file uploaded successfully, extracting images now. It might take some time...'
		try:
			extractThread = Process(target=extractTarBall,args=(filename,course,assign,course_id,assign_id))
			extractThread.start()
		except:
			msg = 'background process creation for image extraction failed'
		redirect(URL(r=request,f='index?msg='+msg))
	elif form.errors:
		response.flash = 'upload has errors'
	else:
		response.flash = 'upload the images as a .tar folder'

	return dict(form=form)

def insertImageToDB(imagepath,filename,course_id,assign_id):
	stream = open(imagepath,'rb')
	db.Submission.insert(image=db.Submission.image.store(stream,filename),course=course_id,assign=assign_id)
	db.commit()
	stream.close()
	return

def extractTarBall(filename,course,assign,course_id,assign_id):
	msg = ''
	try :
		tar = tarfile.open(os.path.join(request.folder,'temps/solution/'+filename))
		expath = os.path.join(request.folder,'temps/solution/parse/'+course+'-'+assign) #The folder is stored as coursename+assignname(to avoid confusion)
		os.makedirs(expath)
		tar.extractall(path=expath)
		for i in os.listdir(expath):
			imagepath = expath+'/'+i
			if os.path.isdir(imagepath):
				for j in os.listdir(imagepath):
					insertImageToDB(imagepath+'/'+j,j,course_id,assign_id)
			else:
				insertImageToDB(imagepath,i,course_id,assign_id)
		try:
			os.system('rm -rf '+expath.replace(' ','\ ')) # Removes the temporarily stored images and upload file. (verified (Y))
			os.system('rm '+ os.path.join(request.folder,'temps/solution/'+filename.replace(' ','\ ')))
		except:
			pass
			#################################################
	#Todo: 	# Put the actual admins email-id over here		#
			#################################################
		os.system('echo "Solution Images Uploaded" | mail -s test develop13mohit@gmail.com')
		response.flash = 'images successfully extracted'
	except:
		response.flash = 'image extraction from folder '+course+'-'+assign+' failed!'

def processFile(filename):
	msg = ''
	try:
		tree = ET.parse(os.path.join(request.folder,'temps/assignment/'+filename))
		root = tree.getroot()
		assign_name = root.attrib['name']
		course_code = root.attrib['ccode']
		course_id = db(db.Course.code == course_code).select(db.Course.id)[0]
#		assign_num = root.attrib['num']
		assign_start_time = root.attrib['start']
		assign_end_time = root.attrib['end']
		assign_id = db.Assign.insert(course=course_id,num=assign_num,start_time=assign_start_time,end_time=assign_end_time,name=assign_name)
		
		for child in root:
			prob_num = child.attrib['num']
			prob_statement = child.find('statement').text
			prob_image = child.find('image').text
			prob_st_time = child.attrib['start']
			prob_end_time = child.attrib['end']
			prob_id = db.Problem.insert(assign=assign_id,num=prob_num,question=prob_statement,image=prob_image,start_time=prob_st_time,end_time=prob_end_time)
			
			ta_list = (child.find('ta').text).split(',')
	
			for ta_mail in ta_list:
				ta_id = db(db.auth_user.email == int(ta_mail)).select(db.auth_user.id,db.auth_user.email)[0]

			########################################################################################
			## We need to take care of something like making the user a TA if he aint already one ##
			########################################################################################

				db.TaProb.insert(ta=ta_id['id'],prob=prob_id)
				os.system('echo "You have been alloted a new question to check. Check ___server address___" | mail -s NewQuestionAlloted'+ta_id['email'])
		mail_data = db((db.StudCourse.course == course_id) & (db.StudCourse.student == db.auth_user.id)).select(db.auth_user.email)
		for user in mail_data:
			os.system('echo "A new assignment has been uplaoded, check portal now!" | mail -s NewAssignment '+user['email'])
		msg = 'Assignment Uploaded'
	except:
		msg = 'xml-file parse failed'
	return msg


def solutionImageTag():
    if auth.user.usertype=='Student' or auth.user.usertype=='TA':
        msg = 'Access Denied!'
        redirect(URL(r=request,f='index?msg=%s' % (msg)))

    courses = db((db.Course.id>0)& (db.Assign.course==db.Course.id)).select(db.Course.id,db.Course.name,db.Assign.id,db.Assign.name)
    if request.vars:
        try:
            assign = int(request.vars['assign'])
        except:
            assign = int(request.vars['assign'][0])
        img = db((db.Assign.course==db.Course.id) & (db.Assign.id == assign) & (db.Submission.assign == assign) & (db.Submission.student==None)).select(db.Submission.ALL).first()
        db.Submission.id.readable=False
        db.Submission.id.writable=False
        db.Submission.image.readable=False
        db.Submission.image.writable=False
        db.Submission.marked.readable=False
        db.Submission.marked.writable=False
        #db.Submission.student="get suggested student"
        if img:
            pre_problem=db(db.Problem.assign == img['assign']).select(db.Problem.id)
            probs=[]
            for i in range(len(pre_problem)):
                probs.append(pre_problem[i]['Problem.id'])
            db.Submission.problem.requires=IS_IN_DB(db(db.Problem.assign == img['assign']),'Problem.id','Problem.num')
            form=SQLFORM(db.Submission,img)
            if form.process().accepted:
                session.flash = 'solution tagged'
                redirect(URL(r=request,f='solutionImageTag?assign=%s' % (assign)))
            elif form.errors:
                response.flash = 'error tagging the image'
        else:
            session.flash = 'All images tagged'
            redirect(URL(r=request,f='index'))
    return locals()

@auth.requires_login()
def TAinterface():
	if auth.user.usertype == 'TA':
		problems = ''
		prob_data = []
		all_problems = db((db.TaProb.ta == auth.user.id) & (db.Problem.id == db.TaProb.prob) & (db.Problem.assign == db.Assign.id) &(db.Course.id == db.Assign.course)).select(db.Problem.id,db.Assign.id,db.Problem.question,db.Assign.name,db.Course.name, orderby = db.Assign.name)
		if request.vars:
			try:
				assign = int(request.vars['assign'])
			except:
				assign = int(request.vars['assign'][0])
			problems = db((db.TaProb.ta == auth.user.id) & (db.Course.id == db.Assign.course)&(db.Problem.id == db.TaProb.prob) & (db.Problem.assign == assign) & (db.Assign.id == assign)).select(db.Problem.id,db.Assign.id,db.Problem.question,db.Assign.name,db.Course.name, orderby = db.Assign.name)
			
			for prob in problems:
				prob_total = db(db.Submission.problem == prob['Problem']['id']).select()
				prob_check = db((db.Submission.problem == prob['Problem']['id']) & (db.Submission.marked == True)).select()
				prob_data.append([len(prob_total),len(prob_check)])
		else:
                        problems=all_problems
                        for prob in problems:
							prob_total = db(db.Submission.problem == prob['Problem']['id']).select()
							prob_check = db((db.Submission.problem == prob['Problem']['id']) & (db.Submission.marked == True)).select()
							prob_data.append([len(prob_total),len(prob_check)])
                assignments_of_ta={}
                for i in range(len(all_problems)):
                    assignments_of_ta[all_problems[i].Assign.id]=[all_problems[i].Course.name,all_problems[i].Assign.name]
        else:
		msg = 'Access Denied!'
		redirect(URL(r=request,f='index?msg=%s' % (msg)))
	return locals()

@auth.requires_login()
def studupload():
	if auth.user.usertype!='Student' and auth.user.usertype!='TA':
		msg = 'Access Denied!'
		redirect(URL(r=request,f='index?msg=%s' % (msg)))

	if request.vars:
		if request.vars:
			if request.vars.assign:
				assign_no=request.vars.assign
			else:
				prob_no=request.vars.problem
				assign_no=db(db.Problem.id==prob_no).select(db.Problem.assign).first()['assign']
			problems=db((db.Problem.assign==assign_no)).select(db.Problem.id,db.Problem.num,db.Problem.end_time)
			studprobs = {}
			for i in range(len(problems)):
				 studprobs[problems[i].id]=problems[i].num
			db.Submission.student.readable=False
			db.Submission.student.writable=False
			db.Submission.assign.readable=False
			db.Submission.assign.writable=False
			db.Submission.course.readable=False
			db.Submission.course.writable=False
			db.Submission.marked.readable=False
			db.Submission.marked.writable=False
			db.Submission.problem.requires=IS_IN_SET(studprobs)
			db.Submission.image.uploadfolder=os.path.join(request.folder,'uploads')
			form = SQLFORM.factory(db.Submission)
			form.vars.student=auth.user.id
			assign_course = db((db.Assign.id==assign_no)).select(db.Assign.id,db.Assign.course).first()
			form.vars.assign = assign_course['id']
			form.vars.course = assign_course['course']
			
			if form.process().accepted:
				problem_end_time= problems[0].end_time
				current_time = datetime.datetime.now()
				diff_time= (time.mktime(problem_end_time.timetuple()) - time.mktime(current_time.timetuple()))
				if diff_time<0:
					session.flash =T("Assignment Deadline Passed")
					redirect(URL('default','studentInterface'))

				already_submitted= db((db.Submission.problem == form.vars.problem)&(db.Submission.student == form.vars.student)).select()
				stream = open(os.path.join(request.folder,'uploads',form.vars.image),'rb')
				if len(already_submitted)==0:		
					db.Submission.insert(student=form.vars.student,course=form.vars.course,\
						assign=form.vars.assign,problem=form.vars.problem,image=db.Submission.image.store(stream,form.vars.image),\
						answer=form.vars.answer,marked=form.vars.marked)
				else:
					stream = open(os.path.join(request.folder,'uploads',form.vars.image),'rb')
					db((db.Submission.student==form.vars.student)&(db.Submission.course==form.vars.course)
						&(db.Submission.assign==form.vars.assign)&(db.Submission.problem==form.vars.problem))\
					.update(image=db.Submission.image.store(stream,form.vars.image),answer=form.vars.answer,marked=form.vars.marked)
				stream.close()
				session.flash =T("Assignment Uploaded Succesfully")
				redirect(URL('default','studentInterface'))
			elif form.errors:
				response.flash = 'form has errors'
	
	assignments = db((db.StudCourse.student==auth.user.id) & (db.StudCourse.course==db.Assign.course) &(db.Course.id==db.StudCourse.course)).select(db.Assign.id,db.Assign.name,db.Course.name)
	
	return locals()

@auth.requires_login()
def checking():
	if auth.user.usertype == 'TA':
		if request.vars:
			try:
				prob = int(request.vars['problem'])
			except:
				prob = int(request.vars['problem'][0])
			
			submission = db((db.Submission.problem == prob) & (db.Submission.student is not None) &  ((db.Submission.marked == None) or (db.Submission.marked==False))).select().first()
                        try:
				p_id = submission['problem']
				check = db((db.TaProb.ta == auth.user.id) & (db.TaProb.prob == p_id)).select()
				if len(check)==0:
					redirect(URL('default','TAinterface'))

			except:
                                if(submission==None):
                                    session.flash = 'All Answer Sheets Checked'
                                    redirect(URL('default','TAinterface'))

				session.flash = 'Access Denied'
				redirect(URL('default','TAinterface'))
			db.SubmitReview.id.readable=False
			db.SubmitReview.id.writable=False
			db.SubmitReview.student.readable=False
			db.SubmitReview.student.writable=False
			db.SubmitReview.ta.readable=False
			db.SubmitReview.ta.writable=False
			db.SubmitReview.problem.readable=False
			db.SubmitReview.problem.writable=False 
			db.SubmitReview.assign.readable=False
			db.SubmitReview.assign.writable=False
			if submission:
                           db.SubmitReview.assign.default=submission['assign']
                           db.SubmitReview.student.default=submission['student']
                           db.SubmitReview.ta.default=auth.user_id
                           db.SubmitReview.problem.default=prob
                           form = SQLFORM(db.SubmitReview)
                           if form.process().accepted:
                               session.flash = 'Marks entered succesfully'
                               db(db.Submission.id == submission['id']).update(marked = True)
                               user = db((db.Submission.id == submission['id']) & (db.Submission.student == db.auth_user.id)).select(db.auth_user.email)[0]
                               os.system('echo "Your submission has been marked, check portal now!" | mail -s SolutionChecked '+ user['email'])
                               redirect(URL(r=request,f='checking?problem=%d' %(prob)))
                           else:
                               session.flash = 'Error entering the marks'
			else:
                            session.flash = 'All solutions checked!'
                            redirect(URL(r=request,f='TAinterface'))
		else:
			response.flash = 'Click on one of the assigned problems'
			redirect(URL(r=request,f='TAinterface'))
	else:
		msg = 'Access Denied!'
		redirect(URL(r=request,f='index?msg=%s' % (msg)))
	return locals()

@auth.requires_login()	
def adminInterface():
	if auth.user.usertype == 'Admin':
		if request.vars:
			try:
				course = int(request.vars['course'])
				ta_list = request.vars['tas']
				tas = ta_list.split(',')
				try:
					for ta in tas:
						ta_id = db(db.auth_user.email == ta).select(db.auth_user.id)[0]
						db.TaCourse.insert(ta=ta_id['id'],course=course)
						db(db.auth_user.id == ta_id['id']).update(usertype='TA')
					response.flash = 'TA allocation successful'
				except:
				 	response.flash = 'TA allocation failed!'
			except:
				course = int(request.vars['course'])
				fac = request.vars['faculty']
				try:
					fac_id = db(db.auth_user.username == fac).select(db.auth_user.id,db.auth_user.first_name)[0]
					cor = db(db.Course.id == course).select(db.Course.name)[0]
					db.FacCourse.insert(faculty = fac_id['id'], course = course)
					db(db.auth_user.id == fac_id['id']).update(usertype='Faculty')
					response.flash = fac_id['first_name']+' is now faculty for '+cor['name']
				except:
				 	response.flash = 'Faculty assigment failed!'
		courses = db(db.Course.id>0).select(db.Course.id,db.Course.name)

	else:
		session.flash = 'Access Denied'
	return locals()

@auth.requires_login()
def addCourse():
	if auth.user.usertype == 'Admin':
		form = SQLFORM(db.Course)
		if form.process().accepted:
			session.flash = 'Course added successfully'
			redirect(URL('default','adminInterface'))
		else:
			session.flash = 'Course addition failed'
	return locals()

@auth.requires_login()
def registerCourse():
	db.StudCourse.student.default = auth.user.id
	db.StudCourse.student.readable = False
	db.StudCourse.student.writable = False
	form = SQLFORM(db.StudCourse)
	if form.process().accepted:
		response.flash = 'Course Registered Successfully'
	else:
		response.flash = 'Course Registration Failed'
	cur_course=db((db.StudCourse.student==auth.user.id) & (db.Course.id == db.StudCourse.course)).select(db.Course.name,db.Course.code)
	return locals()

@auth.requires_login()
def studentInterface():
	if auth.user.usertype!='Student' and auth.user.usertype!='TA':
		msg = 'Access Denied!'
		redirect(URL(r=request,f='index?msg=%s' % (msg)))
		
	if request.vars:
		try:
			assign = int(request.vars['assign'])
		except:
			assign = int(request.vars['assign'][0])
		
                course = db((db.Assign.id == assign) &(db.Assign.course == db.Course.id)).select(db.Course.id).first()
		userData = db((db.SubmitReview.student == auth.user.id) & (db.Submission.course == course) & (db.Submission.assign ==assign) & (db.Submission.student == auth.user.id) & (db.Submission.problem == db.SubmitReview.problem)).select(db.SubmitReview.ALL,db.Submission.image,orderby = db.Submission.id)	
	else:	
		userData = db((db.SubmitReview.student == auth.user.id) & (db.Submission.student == auth.user.id) & (db.Submission.problem == db.SubmitReview.problem)).select(db.SubmitReview.ALL,db.Submission.image,orderby = db.Submission.id)
	assignments= db((db.StudCourse.student == auth.user.id) & (db.StudCourse.course==db.Course.id)&(db.Course.id==db.Assign.course)).select(db.Assign.name,db.Course.name,db.Assign.id)        
        return locals()

@auth.requires_login()
def facultyInterface():
	if auth.user.usertype == 'Faculty':
		assign = None
		if request.vars['assign']:
			try:
				assign = int(request.vars['assign'])
				assignName = db(db.Assign.id == assign).select(db.Assign.name)[0]['name']
				assignData = db(db.Problem.assign == assign).select()
			except:
				assign = int(request.vars['assign'][0])
				assignName = db(db.Assign.id == assign).select(db.Assign.name)[0]['name']
				assignData = db(db.Problem.assign == assign).select()
			
			submissionStat = db(db.Submission.assign == assign).select(db.Submission.ALL)
			try:
				course = submissionStat[0]['course']
			except:
				course = db(db.Assign.id == assign).select(db.Assign.course)[0]['course']
			sub_tot = 0
			sub_marked = 0
			users = []
			users.append('None') #As when we dont have images tagged. Student name is None, we dont have to count that.
			for sub in submissionStat:
				if sub['student'] not in users:
					sub_tot += 1
					users.append(sub['student'])
					if sub['marked'] == True:
						sub_marked += 1
			totalStudents = db(db.StudCourse.course == course).select(db.StudCourse.ALL)
			users = []
			stud_tot = 0
			users.append('None')
			for student in totalStudents:
				if student['student'] not in users:
					users.append(student['student'])
					stud_tot += 1
			
		if request.vars['course']:
			try:
				course = int(request.vars['course'])
			except:
				course = int(request.vars['course'][0])

			facData = db((db.FacCourse.faculty == auth.user.id) & (db.FacCourse.course == course) & (db.Assign.course == course) & (db.Course.id == db.Assign.course)).select(db.Assign.ALL,db.Course.name,db.Course.code,db.Course.id, orderby = db.Course.id)
		
		allfacData = db((db.FacCourse.faculty == auth.user.id) & (db.Assign.course == db.FacCourse.course) & (db.Course.id == db.Assign.course)).select(db.Assign.ALL,db.Course.name,db.Course.code,db.Course.id, orderby = db.Course.id)
		faccourses ={}
		for i in range(len(allfacData)):
			faccourses[i+1]=[allfacData[i].Assign.course,allfacData[i].Course.name]
			
	else:
		msg = 'Access Denied!'
		redirect(URL(r=request,f='index?msg=%s' % (msg)))
	return locals()
		
		
		#########################################################################################################################
#To-Do: # Can we use this feature of 'group membership' (used below in controller) for our TA/Admin/Faculty/Student interfaces? #
		# Never used this before. @auth.requires_membership('group name')														#
		#########################################################################################################################
	

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/manage_users (requires membership in
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())

@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())
