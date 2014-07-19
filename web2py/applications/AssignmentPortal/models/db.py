# -*- coding: utf-8 -*-

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    db = DAL('sqlite://storage.sqlite',pool_size=1,check_reserved=['all'])
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
## (optional) static assets folder versioning
# response.static_version = '0.0.0'
#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Crud, Service, PluginManager, prettydate
auth = Auth(db)

from gluon.contrib.login_methods.cas_auth import CasAuth

auth.settings.extra_fields['auth_user'] = [
		Field('user_type',requires=IS_IN_SET(['Student','TA','Faculty','Admin']),default='Student'),
		Field('roll_no','integer')]

crud, service, plugins = Crud(db), Service(), PluginManager()

## create all tables needed by auth if not custom tables
auth.define_tables(username=True, signature=False)

auth.settings.login_form=CasAuth(
            urlbase = "https://login.iiit.ac.in/cas",
            actions = ['login','validate','logout'],
            casversion = 2,
            casusername = "cas:user")


## configure email
mail = auth.settings.mailer
mail.settings.server = 'logging' or 'smtp.gmail.com:587'
mail.settings.sender = 'you@gmail.com'
mail.settings.login = 'username:password'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = False
auth.settings.actions_disabled=['register','change_password','verify_email','retrieve_username','request_reset_password','reset_assword']
auth.settings.login_next = URL('index')
auth.settings.profile_next = URL('index')


## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
from gluon.contrib.login_methods.rpx_account import use_janrain
use_janrain(auth, filename='private/janrain.key')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################

import os

db.define_table('Course',
		db.Field('name','string',required=True),
		db.Field('code','string',required=True)
		)

db.define_table('UploadedAssign',
		db.Field('filename','upload',uploadfolder=os.path.join(request.folder,'temps/assignment/tar')),
		db.Field('student',db.auth_user,requires=IS_IN_DB(db,'auth_user.id','auth_user.first_name'))
		)

db.define_table('Assign',
		db.Field('course',db.Course,requires=IS_IN_DB(db,'Course.id','Course.name')),
		db.Field('name','string'),
		db.Field('num','integer',required=True),
		db.Field('start_time','datetime',default=request.now),
		db.Field('end_time','datetime',default=request.now)
		)
			
db.define_table('Problem',
		db.Field('assign',db.Assign,requires=IS_IN_DB(db,'Assign.id','Assign.name')),
		db.Field('num','integer',required=True,unique=True),
		db.Field('question','string',required=True),
		db.Field('image','upload'),
		db.Field('start_time','datetime',default=request.now),
		db.Field('end_time','datetime',default=request.now)
		)

#Not so sure about this. Plej review#
db.define_table('TaProb',
		db.Field('ta',db.auth_user,requires=IS_IN_DB(db,'auth_user.id','auth_user.first_name')),
		db.Field('prob',db.Problem,requires=IS_IN_DB(db,'Problem.id','Problem.num'))
		)

db.define_table('StudCourse',
		db.Field('student',db.auth_user,requires=IS_IN_DB(db,'auth_user.id','auth_user.first_name')),
		db.Field('course',db.Course,requires=IS_IN_DB(db,'Course.id','Course.name'))
		)

db.define_table('Submission',
		db.Field('student',db.auth_user,requires=IS_IN_DB(db,'auth_user.id','auth_user.first_name')),
		db.Field('assign',db.Assign,requires=IS_IN_DB(db,'Assign.id','Assign.name')),
		db.Field('problem',db.Problem,requires=IS_IN_DB(db,'Problem.id','Problem.num')),
		db.Field('image','upload'),
		db.Field('answer','string')
		)

db.define_table('AutoAssign',
		db.Field('upfile','upload',uploadfolder=os.path.join(request.folder,'temps/assignment'))
		)

db.define_table('ImageStack',
		db.Field('course',db.Course,requires=IS_IN_DB(db,'Course.id','Course.name')),
		db.Field('assign',db.Assign,requires=IS_IN_DB(db,'Assign.id','Assign.name')),
		db.Field('upfile','upload',uploadfolder=os.path.join(request.folder,'temps/solution'))
		)

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)