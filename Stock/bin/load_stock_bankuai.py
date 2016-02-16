#!/usr/local/bin/python2.7
#coding:utf-8

import sys,os,re,datetime,csv

from optparse import OptionParser
from common_tool import replace_vars, print_log, warn_log, error_log, get_date, get_yaml
from psql import get_conn, get_cur
from loader.load_into_bankuai import load_into_bankuai
from loader.load_into_stock import load_into_stock
from loader.load_into_stock_bankuai import load_into_stock_bankuai

#-- sys var
SEP = os.path.sep
FILE_PATH = os.getcwd()
FILE_BASE_NAME = __file__
FILE_NAME = FILE_PATH + SEP + FILE_BASE_NAME
PROJ_BASE_DIR = FILE_PATH + SEP + ".."
YML_DIR = PROJ_BASE_DIR + SEP + "etc"
DATA_DIR = PROJ_BASE_DIR + SEP + "data"
LOG_DIR = PROJ_BASE_DIR + SEP + "log"
DB_YML = YML_DIR + SEP + "db.yml"

table_mapping = {
	"dim_bankuai": {
		"load_seq": 1, 
		"func_name": "load_into_bankuai", 
		"param": "conn, '$f'",
		"file": [DATA_DIR + SEP + "bankuai_$DATE.csv"]}, 
	"dim_stock": {
		"load_seq": 2, 
		"func_name": "load_into_stock", 
		"param": "conn, '$f'",
		"file": [DATA_DIR + SEP + "bankuai_stock_$DATE.csv"]}, 
	"dim_stock_bankuai": {
		"load_seq": 3, 
		"func_name": "load_into_stock_bankuai", 
		"param": "conn, '$f'",
		"file": [DATA_DIR + SEP + "bankuai_stock_$DATE.csv"]}, 
}
#-- file load seq, based on load_seq in table_mapping, put table names into load_seq_tables in a sorted order
load_seq_mapping = {}
for i in table_mapping:
	load_seq_mapping[table_mapping[i]["load_seq"]] = i
load_seq_tables = [load_seq_mapping[i] for i in load_seq_mapping]

today = get_date("today")
yesterday = get_date("yesterday")
start_date = ""
end_date = ""
files_to_load = {}


#-- opts
parser = OptionParser()
parser.add_option("--start_date", "-s", dest="start_date", action="store", type="string", default=today, help="Start date of the date range, e.g. 20150101")
parser.add_option("--end_date", "-e", dest="end_date", action="store", type="string", default=today, help="End date of the date range, e.g. 20150101")
parser.add_option("--table", "-t", dest="table", action="store", type="string", help="dim_bankuai|dim_stock|dim_stock_bankuai")
parser.add_option("--in_file", "-f", dest="in_file", action="store", type="string", help="To load a specific file, $DATE would be replaced from --start_date and --end_date")
(options, args) = parser.parse_args()

#-- var assignment
vars_for_none_check = []
start_date = options.start_date
end_date = options.end_date

#-- function
def exit_process():
	os.system("python " + FILE_NAME + " -h")
	sys.exit()
	
def exit_for_none_var(var):
	if eval("options." + var) is None:
		error_log(var + " must be assigned!")
		exit_process()
		
def return_parent_bankuai_ids(db_conn):
	query = "SELECT ID, NAME FROM DW.DIM_PARENT_BANKUAI"
	cur = get_cur(db_conn)
	cur.execute(query)
	rows = list(cur)
	return_dict = {}
	for row in rows:
		return_dict[row["name"].decode("utf-8")] = row["id"]
	cur.close()
	return return_dict

	
#-- iterate vars for none check
[exit_for_none_var(var) for var in vars_for_none_check]

#-- verify param
if not (re.match("^\d{8}$", start_date) and re.match("^\d{8}$", end_date)):
	error_log("start_date or end_date error! [" + start_date + "][" + end_date + "]")
	exit_process()
elif start_date > end_date:
	error_log("start_date must be smaller than end_date! [" + start_date + "][" + end_date + "]")
	exit_process()

#-- determine file to load, $DATE is not replaced
if options.in_file is None:
	if options.table is None:
		for tab in table_mapping:
			files_to_load[tab] = table_mapping[tab]["file"]
	elif options.table in table_mapping:
		files_to_load = {options.table: table_mapping[options.table]["file"]}
	else: 
		error_log("table is not correct! [" + options.table + "]")
		exit_process()
else:
	if options.table in table_mapping:
		files_to_load = {options.table: [options.in_file]}
	else:
		error_log("table is not correct! [" + options.table + "]")
		exit_process()

#-- replace $DATE, it will check the existence of files, if file doesn't exist, it wouldn't be added to the loading list
start_dt_dt = datetime.datetime.strptime(start_date, "%Y%m%d")
end_dt_dt = datetime.datetime.strptime(end_date, "%Y%m%d")

for k,v in files_to_load.items():
	dt_replaced = []
	process_dt_dt = start_dt_dt
	while process_dt_dt <= end_dt_dt:
		process_dt = datetime.datetime.strftime(process_dt_dt, "%Y%m%d")
		if os.path.isfile(v[0].replace("$DATE", process_dt)):
			dt_replaced.append(v[0].replace("$DATE", process_dt))
		else:
			warn_log(v[0].replace("$DATE", process_dt) + " doesn't exist." )
		process_dt_dt = process_dt_dt + datetime.timedelta(1)
	files_to_load[k] = dt_replaced


#-- fetch DB info
db_dict = get_yaml(DB_YML)

#-- open db connection
conn = get_conn(db_dict["DB"], db_dict["Username"], db_dict["Password"], db_dict["Host"], db_dict["Port"])

#-- get the dict of parent bankuai id and name
parent_bankuai_ids = return_parent_bankuai_ids(conn)

#------------------------------------------- LOADing
for t in load_seq_tables:
	if t in files_to_load:
		for f in files_to_load[t]:
			cmd = "%(func_name)s(%(param)s)" % {"func_name": table_mapping[t]["func_name"], "param": table_mapping[t]["param"]}
			cmd_with_filename = cmd.replace("$f", f.replace('\\', '\\\\')) # replace \\ with \\\\ is just for windows platform, unix/linux platform won't be impacted
			eval(cmd_with_filename)

conn.close()



