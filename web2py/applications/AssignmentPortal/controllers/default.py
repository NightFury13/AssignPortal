# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################

import os
import tarfile
import xml.etree.ElementTree as ET
import threading
from multiprocessing import Process
def index():
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html

    if you need a simple wiki simply replace the two lines below with:
    return auth.wiki()
    """
    msg = request.vars['msg']    
    if not msg:
	    msg = 'Welcome'
    response.flash = T(msg)
    return dict(message=T('Hello World'))

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
	form = SQLFORM(db.ImageStack)
	if form.process().accepted:
		filename = form.vars.upfile
		course = form.vars.course
		course = db(db.Course.id == course).select(db.Course.name).first()
		course = course.name
		assign = form.vars.assign
		assign = db(db.Assign.id == assign).select(db.Assign.name).first()
		assign = assign.name
		#extractTarBall(filename,course,assign)
		msg = 'file uploaded successfully, extracting images now. It might take some time...'
		try:
			extractThread = Process(target=extractTarBall,args=(filename,course,assign))
			extractThread.start()
		except:
			msg = 'background process creation for image extraction failed'
		redirect(URL(r=request,f='index?msg='+msg))
	elif form.errors:
		response.flash = 'upload has errors'
	else:
		response.flash = 'upload the images as a .tar folder'

	return dict(form=form)

def insertImageToDB(imagepath,filename):
	stream = open(imagepath,'rb')
	db.Submission.insert(image=db.Submission.image.store(stream,filename))
	db.commit()
	stream.close()
	return

def extractTarBall(filename,course,assign):
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
					insertImageToDB(imagepath+'/'+j,j)
			else:
				insertImageToDB(imagepath,i)
		try:
			os.system('rm -rf '+expath.replace(' ','\ '))
			os.system('rm '+ os.path.join(request.folder,'temps/solution/'+filename.replace(' ','\ ')))
		except:
			pass
		response.flash = 'images successfully extracted'
	except:
		response.flash = 'image extraction from folder '+course+'-'+assign+' failed!'

def uploadAssignment():
    form=SQLFORM(db.UploadedAssign)
    form.vars.student=auth.user.id
    if form.process().accepted:
        filename=form.vars.filename
        msg=processTar(filename)
        redirect(URL(r=request,f='index?msg='+msg))
    elif form.errors:
        response.flash='Form Error!'
    return dict(form=form)

def processTar(filename):
    tar=tarfile.open(os.path.join(request.folder,'temps/assignment/tar/'+filename))
    expath=os.path.join(request.folder,'temps/assignment/tar/parse/'+filename.split('.')[2])
    os.makedirs(expath)
    tar.extractall(path=expath)
    tree=ET.parse(os.path.join(expath,'meta.xml'))
    root=tree.getroot()
    course_code=root.attrib['ccode']
    course_id=db(db.Course.code==course_code).select(db.Course.id)[0]
    assign_num=root.attrib['num']
    assign_id=db((db.Assign.num==assign_num) & (db.Assign.course==course_id)).select(db.Assign.id)[0]
    for problem in root.findall('problem'):
        prob_id=problem.attrib['id']
        img_path=os.path.join(expath,problem.find('img').text)
        answer_text=problem.find('text').text
        db.Submission.insert(student=auth.user.id,assign=assign_id,problem=prob_id,image=img_path,answer=answer_text)
    return 'Upload Successful'

def processFile(filename):
	msg = ''
	try:
		tree = ET.parse(os.path.join(request.folder,'temps/assignment/'+filename))
		root = tree.getroot()
		course_code = root.attrib['ccode']
		course_id = db(db.Course.code == course_code).select(db.Course.id,db.Course.id)[0]
		assign_num = root.attrib['num']
		assign_start_time = root.attrib['start']
		assign_end_time = root.attrib['end']
		assign_id = db.Assign.insert(course=course_id,num=assign_num,start_time=assign_start_time,end_time=assign_end_time)
		
		for child in root:
			prob_num = child.attrib['num']
			prob_statement = child.find('statement').text
			prob_image = child.find('image').text
			prob_st_time = child.attrib['start']
			prob_end_time = child.attrib['end']
			prob_id = db.Problem.insert(assign=assign_id,num=prob_num,question=prob_statement,image=prob_image,start_time=prob_st_time,end_time=prob_end_time)
			
			ta_list = (child.find('ta').text).split(',')
		
			for ta_roll in ta_list:
				ta_id = db(str(db.auth_user.roll_no) == ta_roll).select(db.auth_user.id,db.auth_user.id)[0]
				db.TaProb.insert(ta=ta_id,prob=prob_id)
		msg = 'Assignment Uploaded'
	except:
		msg = 'xml-file parse failed'
	return msg

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
