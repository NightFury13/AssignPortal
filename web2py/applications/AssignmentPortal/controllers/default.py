# -*- coding: utf-8 -*-

import os
import tarfile
import xml.etree.ElementTree as ET
import threading
import datetime
import time
# For PDF creation
import sys,cStringIO
import xhtml2pdf.pisa as pisa
from multiprocessing import Process
import json
def index():
	msg = request.vars['msg']    
	if not msg:
		msg = 'Welcome'
	response.flash = T(msg)
	return dict(login_form=auth.login(),message=T('Hello World'))

# For PDF creation
def html2pdf():
	import gluon.contrib.simplejson
	newdata = gluon.contrib.simplejson.loads(request.body.read())
	data=str(newdata["html"])
	filename=str(newdata["filename"])
	original_file=filename
	filename=os.path.join(request.folder,'uploads/'+filename)
	pdf=pisa.CreatePDF(cStringIO.StringIO(data),file(filename,"wb"))
	return original_file

def download_pdf():
	filename=request.args[0]
	filename=os.path.join(request.folder,'uploads/'+filename)
	return response.stream(open(filename,'rb'), chunk_size=10**6)

@auth.requires_login()
def student_home():
	if auth.user.usertype == 'Student' or auth.user.usertype == 'TA':
		stud_data = db((db.StudCourse.student==auth.user.id) & (db.StudCourse.course==db.Course.id) & (db.Assign.course==db.Course.id) & (db.Assign.id==db.Problem.assign)).select(db.Course.name,db.Assign.name,db.Assign.end_time,db.Problem.num,db.Problem.id,db.Assign.id)	
	else:
		response.flash == 'Access Denied!'
		redirect(URL(r=request,f='index'))
	return locals()

def course_reg_upload(filename,courseid):
	try:
		filepath=open(os.path.join(request.folder,'uploads/'+filename))
		lines=filepath.readlines()
		for i in lines:
			email=i.strip()
			try:
				userid=db(db.auth_user.email==email).select(db.auth_user.id).first()
				db.StudCourse.insert(student=userid['id'],course=courseid)
			except:
				pass
		filepath.close()
	except:
		pass
	# delete the files for the current course
	db(db.BatchRegisteration.course==courseid).delete()
	db.commit()
	return locals()

@auth.requires_login()
def course_registeration():
	form = ''
	if auth.user.usertype == 'Admin':
		form=SQLFORM(db.BatchRegisteration)
		if form.process().accepted:
			response.flash = 'File Uploaded Successfully'
			filename=form.vars.upload
			courseid=form.vars.course
			popthread = Process(target=course_reg_upload,args=(filename,courseid))
			popthread.start()
		elif form.errors:
			response.flash = 'Error in upload'
	else:
		response.flash = 'Access Denied!'
		redirect(URL(r=request,f='index'))
	return locals()

@auth.requires_login()
def see_marks():
	if auth.user.usertype == 'Student':
		stud_data = db((db.StudCourse.student==auth.user.id) & (db.StudCourse.course==db.Course.id) & (db.Assign.course==db.Course.id) & (db.Assign.id==db.Problem.assign)).select(db.Course.name,db.Assign.name,db.Assign.end_time,db.Problem.num,db.Problem.id,db.Assign.id)	
	else:
		response.flash = 'Access Denied!'
		redirect(URL(r=request,f='index'))
	return locals()

@auth.requires_login()
def see_submission():
	subid = request.vars['subid']
	revid = request.vars['revid']
	return locals()

@auth.requires_login()
def autoAssignment():
	if auth.user.usertype == 'Faculty' or auth.user.usertype == 'TA':
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
	else:
		response.flash = 'Access Denied'
		redirect(URL(r=request,f='index'))
	return dict(form=form)

@auth.requires_login()
def uploadTarBall():
	if auth.user.usertype == 'Admin':
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
			except:
				pass
		form = SQLFORM(db.ImageStack)
		if form.process().accepted:
			filename = form.vars.upfile
			course_id = form.vars.course
			course = db(db.Course.id == course_id).select(db.Course.name).first()
			course = course.name
			assign_id = form.vars.assign
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
	else:
		response.flash = 'Access Denied!'
		redirect(URL(r=request,f='index'))
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
		assign_num = root.attrib['num']
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
			
			check_options = (child.find('checkoptions').text).split(',')
			for opt in check_options:
				param_text = opt.split('*')[0]
				param_id = db.ProbParam.insert(prob=prob_id, param=param_text)
				param_fields = (opt.split('*')[1]).split('/')

				for fld in param_fields:
					paramopt_opt = fld.split('-')[0]
					paramopt_weight = fld.split('-')[1]
					paramopt_id = db.ParamOption.insert(prob=prob_id,param=param_id,opt=paramopt_opt,weight=paramopt_weight)

			ta_list = (child.find('ta').text).split(',')
	
			for ta_mail in ta_list:
				ta_id = db(db.auth_user.email == ta_mail).select(db.auth_user.id,db.auth_user.email)[0]
				db.TaProb.insert(ta=ta_id['id'],prob=prob_id)
				os.system('echo "You have been alloted a new question to check. Check ___server address___" | mail -s NewQuestionAlloted'+ta_id['email'])
		mail_data = db((db.StudCourse.course == course_id) & (db.StudCourse.student == db.auth_user.id)).select(db.auth_user.email)
		for user in mail_data:
			os.system('echo "A new assignment has been uplaoded, check portal now!" | mail -s NewAssignment '+user['email'])
		msg = 'Assignment Uploaded'
	except:
		msg = 'xml-file parse failed'
	return msg

@auth.requires_login()
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
def get_mark_helper():
	if auth.user.usertype == 'Faculty' or auth.user.usertype == 'TA':
		assign=db(db.Assign.id>0).select(db.Assign.id,db.Assign.name)
	else:
		response.flash = 'Access Denied!'
		redirect(URL(r=request,f='index'))
	return locals()

@auth.requires_login()
def get_marks():
	if auth.user.usertype == 'Faculty' or auth.user.usertype == 'TA':
		assign_id=request.vars.assign
		assign_name=db(db.Assign==assign_id).select(db.Assign.name).first()
		marks=db((db.SubmitReview.assign==assign_id)&(db.SubmitReview.student==db.auth_user.id)).select(db.auth_user.first_name,db.auth_user.last_name,db.auth_user.email,db.auth_user.rollno,db.SubmitReview.problem,db.SubmitReview.marks)
	else:
		response.flash = 'Access Denied!'
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
				assign_deadline=db(db.Assign.id==assign_no).select(db.Assign.start_time,db.Assign.end_time).first()
				current_time = datetime.datetime.now()
				diff_af_time=(time.mktime(assign_deadline['end_time'].timetuple()) - time.mktime(current_time.timetuple()))
				diff_as_time= (time.mktime(current_time.timetuple()) - time.mktime(assign_deadline['start_time'].timetuple()))
				if(diff_as_time<0):
					session.flash =T("Assignment Submission Not Yet Started")
					redirect(URL('default','student_home'))
				elif(diff_af_time<0):
					session.flash =T("Assignment Deadline Passed")
					redirect(URL('default','student_home'))
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
			
			#test code
			#check if causing problems with multi assignment(wrote the two lines for studen_Home submit now refirection)
			if request.vars.problem:
				form.vars.problem=request.vars.problem
			#test code ends

			if form.process().accepted:
				problem_end_time= problems[0].end_time
				current_time = datetime.datetime.now()
				diff_time= (time.mktime(problem_end_time.timetuple()) - time.mktime(current_time.timetuple()))
				if diff_time<0:
					session.flash =T("Assignment Deadline Passed")
					redirect(URL('default','student_home'))

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
				redirect(URL('default','student_home'))
			elif form.errors:
				response.flash = 'form has errors'
	
	assignments = db((db.StudCourse.student==auth.user.id) & (db.StudCourse.course==db.Assign.course) &(db.Course.id==db.StudCourse.course)).select(db.Assign.id,db.Assign.name,db.Course.name)
	
	return locals()

@auth.requires_login()
def checking():
	if auth.user.usertype == 'TA':
		if request.vars['problem']:
			try:
				prob = int(request.vars['problem'])
			except:
				prob=int(request.vars['problem'][0])
			submission = db((db.Submission.problem == prob) & (db.Submission.student is not None) &  ((db.Submission.marked == None) or (db.Submission.marked==False))).select().first()
			try:
				p_id = submission['problem']
				check = db((db.TaProb.ta == auth.user.id) & (db.TaProb.prob == p_id)).select()
				if len(check)==0:
					redirect(URL('default','TAinterface'))
			except:
				if(submission==None):
					session.flash = 'All Answer Sheets Checked'
					redirect(URL(r=request,f='TAinterface'))#'AssignmentPortal','default','TAinterface'))
				else:
					response.flash = 'Access Denied'
					redirect(URL('default','TAinterface'))
			all_params = db(db.ProbParam.prob == prob).select(db.ProbParam.param)
			params = {}
			for para in all_params:
				temp = para['param']
				params[temp] = []
				opts = db((db.ProbParam.prob==prob)&(db.ParamOption.param == db.ProbParam.id) & (db.ProbParam.param == temp)).select(db.ParamOption.opt,db.ParamOption.weight)
				for opt in opts:
					params[temp].append(opt['opt']+'('+str(opt['weight'])+')')
		#	except:
		#		prob = int(request.vars['problem'][0])

			if len(request.vars)>1:#for case where we get more parameters like comment/neatness etc with problem id
				try:
					all_opt=dict(request.vars)
					del all_opt['comments']
					del all_opt['problem']
					all_opts=[]
					for i in all_opt:
						all_opts.append(all_opt[i])
					#all_opts = request.vars['opt']
					comms = request.vars['comments']
				#	db.SubmitReview.assign.default=submission['assign']
				#	db.SubmitReview.student.default=submission['student']
				#	db.SubmitReview.ta.default=auth.user_id
				#	db.SubmitReview.problem.default=prob
				#	db.SubmitReview.comments.default=comms
					marks = 0
					for option in all_opts:
						p = db(db.ProbParam.param == option.split('+')[0]).select(db.ProbParam.id)[0]
						o = db(db.ParamOption.opt == option.split('+')[1].split('(')[0]).select(db.ParamOption.id)[0]
						db.SubRevParam.insert(submission=submission['id'],student=submission['student'],param=p)
						marks += int(option.split('(')[1].split(')')[0])
				#	db.SubmitReview.marks.default=marks
					db.SubmitReview.insert(assign=submission['assign'],student=submission['student'],ta=auth.user.id,problem=prob,comments=comms,marks=marks)
					session.flash = 'Marks entered succesfully'
					db(db.Submission.id == submission['id']).update(marked = True)
					user = db((db.Submission.id == submission['id']) & (db.Submission.student == db.auth_user.id)).select(db.auth_user.email)[0]
					os.system('echo "Your submission has been marked, check portal now!" | mail -s SolutionChecked '+ user['email'])

				except:
					session.flash = 'Error entering the marks'
				
				redirect(URL(r=request,f='checking?problem=%d' %(prob)))
#			else:
#				session.flash = 'All solutions checked!'
#				redirect(URL(r=request,f='TAinterface'))
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
		response.flash = 'Access Denied'
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
        if request.vars:
            course_id=db(db.StudCourse.student==auth.user.id).select(db.StudCourse.course)
            for i in course_id:
                if int(i['course'])==int(request.vars['course']):
                    session.flash = "Already Registered for Course"
                    redirect(URL('default','registerCourse'))
        form = SQLFORM(db.StudCourse)
	if form.process().accepted:
		response.flash = 'Course Registered Successfully'
        elif form.errors:
		response.flash = 'Course Registration Failed'
	cur_course=db((db.StudCourse.student==auth.user.id) & (db.Course.id == db.StudCourse.course)).select(db.Course.name,db.Course.code)
	return locals()

@auth.requires_login()
def studentInterface():
	if auth.user.usertype!='Student' and auth.user.usertype!='TA':
		msg = 'Access Denied!'
		redirect(URL(r=request,f='index?msg=%s' % (msg)))
	
	problems = ''	
	if request.vars:
		try:
			assign = int(request.vars['assign'])
		except:
			assign = int(request.vars['assign'][0])
		
		course = db((db.Assign.id == assign) &(db.Assign.course == db.Course.id)).select(db.Course.id).first()
		status = db((db.Submission.student == auth.user.id) & (db.Submission.assign == assign) & (db.Submission.problem == db.Problem.id)).select(db.Submission.id, db.Problem.question, orderby = db.Submission.id)
		userData = db((db.SubmitReview.student == auth.user.id) & (db.Submission.course == course) & (db.Submission.assign ==assign) & (db.Submission.student == auth.user.id) & (db.Submission.problem == db.SubmitReview.problem)).select(db.SubmitReview.ALL,db.Submission.image,db.Submission.id,orderby = db.Submission.id)	
		problems = db((db.Problem.assign == assign) & (db.Problem.assign == db.Assign.id)).select(db.Problem.question,db.Assign.name, orderby = db.Assign.id)
	else:	
		userData = db((db.SubmitReview.student == auth.user.id) & (db.Submission.student == auth.user.id) & (db.Submission.problem == db.SubmitReview.problem)).select(db.SubmitReview.ALL,db.Submission.image,db.Submission.id,orderby = db.Submission.id)
		status = db((db.Submission.student == auth.user.id) & (db.Submission.problem == db.Problem.id)).select(db.Submission.id, db.Problem.question, orderby = db.Submission.id)
	
	assignments= db((db.StudCourse.student == auth.user.id) & (db.StudCourse.course==db.Course.id)&(db.Course.id==db.Assign.course)).select(db.Assign.name,db.Course.name,db.Assign.id)        
        return locals()

@auth.requires_login()
def assignstatus():
	if auth.user.usertype!='Student' and auth.user.usertype!='TA':
		msg = 'Access Denied!'
		redirect(URL(r=request,f='index?msg=%s' % (msg)))

	assignments = db((auth.user.id==db.StudCourse.student)&(db.StudCourse.course==db.Assign.course)).select(db.Assign.ALL)
	current_time = datetime.datetime.now()
	past_flag=0
	if request.vars and (int(request.vars.sort) == 1):
		past_flag=1
		past_assigns=[]
		for i in assignments:
			diff_f_time= (time.mktime(i['end_time'].timetuple()) - time.mktime(current_time.timetuple()))
			diff_s_time= (time.mktime(current_time.timetuple()) - time.mktime(i['start_time'].timetuple()))
			if(diff_f_time<0 and diff_s_time>0):
				diff_f_time= (time.mktime(i['end_time'].timetuple()) - time.mktime(current_time.timetuple()))
				past_assigns.append(i)
	else:
		current_assigns=[]
		for i in assignments:
			diff_f_time= (time.mktime(i['end_time'].timetuple()) - time.mktime(current_time.timetuple()))
			diff_s_time= (time.mktime(current_time.timetuple()) - time.mktime(i['start_time'].timetuple()))
			if(diff_f_time>0 and diff_s_time>0):
				diff_f_time= (time.mktime(i['end_time'].timetuple()) - time.mktime(current_time.timetuple()))
				current_assigns.append(i)
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
