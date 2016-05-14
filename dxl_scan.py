#!/bin/env python

# standard imports
import os,sys
import argparse,exceptions,traceback
import network_specifics
import process_utils
import subprocess
import random,time
import cPickle as pickle
import re
import collections
import hashlib
import operator
import datetime

# custom imports
import python_lacks,project_config,text_progress_bar,drives
import count_usage
from dxl_lexer import Lexer
from template import Template

try:
    import psyco
    psyco.full()
except ImportError:
    print("warning: psyco import error: "+str(sys.exc_info()[1]))

import error_report

class Error:
    def __init__(self, kind, message, line=0):
        self.kind = kind
        self.message = message
        self.line = line

    def __str__(self):
        m = self.kind+": "+self.message
        if isinstance(self.line, str):
            m += " at lines " + self.line
        else:
            if self.line > 0:
                m += " at line %d" % self.line
        return m

class IncludeError(Error):
    def __init__(self, path, kind, line):
        Error.__init__(self, kind, "when including "+path, line)
        Error.__str__(self)
        self.included_path = path

class FunctionError(Error):
    def __init__(self, token, kind, line):
        Error.__init__(self, kind, token, line)
        Error.__str__(self)
        self.token = token

class PragmaError(Error):
    def __init__(self, token, kind, line):
        Error.__init__(self, kind, token, line)
        Error.__str__(self)
        self.token = token

class DuplicateFileError():
    def __init__(self, message, file_path):
        self.message = message
        self.file_path = file_path

    def __str__(self):
        m = self.message+": "+self.file_path
        return m

class OversizeFileError():
    def __init__(self, message):
        self.message = message

    def __str__(self):
        m = self.message
        return m

class DuplicateFunctionError(DuplicateFileError):
    def __init__(self, message, files):
        DuplicateFileError.__init__(self, message, files)
        DuplicateFileError.__str__(self)


class ArgParser(object):
    def __init__(self, version):
        self.__parser = argparse.ArgumentParser(add_help=True)
        self.__main_group = self.__parser.add_argument_group("Specific arguments")
        self.__parser.add_argument('-v', '--version', action='version', version=version)

    def add_argument(self, long_opt, desc, short_opt=None, required=False, default=None):
        # For easy writting, user use '=' at param name end if it receive a value
        # And omit it if this parameter is just a flag
        if long_opt.endswith('='):
            # Store linked value
            action="store"
            # Remove the '=' at end to normalize
            long_opt = long_opt[:-1]
        elif long_opt.endswith('=[]'):
            # Store in an array
            action="append"
            if default == None:
                default = []
            # Remove the '=[]' at end to normalize
            long_opt = long_opt[:-3]
        else:
            # Flag mode
            action="store_true"
            if default == None:
                default = False

        if not short_opt:
            short_opt = long_opt[0]

        self.__main_group.add_argument("-"+short_opt, "--"+long_opt, help=desc, dest=long_opt, action=action, default=default, required=required)

    def accept_positional_arguments(self, name, desc):
        """
            Use this method if positonal arguments are going to be used
        """
        self.__parser.add_argument(name, help=desc, nargs='*', action="store")

    def parse(self,args=None):
        return self.__parser.parse_args(args=args)

class StartDoors:
    __VERSION_NUMBER = "1.0"
    try:
        __MODULE_FILE = sys.modules[__name__].__file__
    except:
        __MODULE_FILE = sys.executable
    __PROGRAM_NAME = os.path.basename(__MODULE_FILE)
    __PROGRAM_DIR = os.path.abspath(os.path.dirname(__MODULE_FILE))


    def __init__(self):
        self.__ARG_PARSER = ArgParser(self.__VERSION_NUMBER)
        self.__logfile = ""
        self.__temp_directory = None
        self.__with_traceback = True
        self.__database = None

        self.__ini_file = os.path.splitext(self.__PROGRAM_NAME)[0]+".ini"

        try:
            # set binary mode on output/error stream for Windows
            import msvcrt
            msvcrt.setmode (sys.stdout.fileno(), os.O_BINARY)
            msvcrt.setmode (sys.stderr.fileno(), os.O_BINARY)
        except:
            pass
    def __create_temp_directory(self):
        """
        defines self.__temp_directory
        """

        self.__temp_directory = os.path.join(os.getenv("TEMP"),self.__PROGRAM_NAME.replace(".py","")+("_%d" % os.getpid()))
        python_lacks.create_directory(self.__temp_directory)
        if self.__verbose:
            self.__message("Created temporary directory %s" % self.__temp_directory)
        return self.__temp_directory

    def __delete_temp_directory(self):
        if self.__temp_directory != None:
            [rc,output] = python_lacks.rmtree(self.__temp_directory)
            if rc == 0:
                self.__temp_directory = None
            else:
                self.__warn("Could not delete temp dir %s: %s" % (self.__temp_directory,output))

    def init_from_custom_args(self,args):
        """
        module mode, with arguments like when called in standalone
        """
        self.__parse_args(args)
        self.__purge_log()
        self.__doit()

    def _init_from_sys_args(self):
        """ standalone mode """
        try:
            self.__do_init()
            self.__delete_temp_directory()
        except SystemExit, se:
            # do not catch user exits
            raise se
        except:
            # catch exception
            if self.__with_traceback:
                # get full exception traceback
                traceback.print_exc()
            msg = python_lacks.ascii_compliant(sys.exc_info()[1].message, best_ascii_approximation=True)
            self.__message(msg)
            #wx_utils.error_message(msg)
            # log exception by e-mail
            error_report.ErrorReport()

            sys.exit(1)
        finally:
            self.__delete_temp_directory()

# uncomment if module mode is required
##    def init(self,output_file):
##        """ module mode """
##        # set the object parameters using passed arguments
##        self.__output_file = output_file
##        self.__purge_log()
##        self.__doit()

    def __do_init(self):
        self.__parse_args()
        self.__purge_log()
        self.__doit()

    def __purge_log(self):
        if self.__logfile != "":
            try:
                os.remove(self.__logfile)
            except:
                pass

    def __message(self,msg,with_prefix=True):
        if with_prefix:
            msg = self.__PROGRAM_NAME+(": %s" % msg)+os.linesep
        else:
            msg += os.linesep
        try:
            sys.stderr.write(msg)
            sys.stderr.flush()
        except:
            # ssh tunneling bug workaround
            pass
        if self.__logfile != "":
            f = open(self.__logfile,"ab")
            f.write(msg)
            f.close()

    def __error(self,msg,user_error=True,with_traceback=False):
        """
        set user_error to False to trigger error report by e-mail
        """
        error_report.ErrorReport.USER_ERROR = user_error
        self.__with_traceback = with_traceback
        raise Exception("*** Error: "+msg+" ***")

    def __warn(self,msg):
        self.__message("*** Warning: "+msg+" ***")
        if self.__mode != self.__OPEN_MODE_BATCH:
            wx_utils.warning_message(msg)

    def __parse_args(self,args=None):
        # Define authorized args
        self.__define_args()

        # Parse passed args
        opts = self.__ARG_PARSER.parse(args=args)
        for key, value in opts.__dict__.items():
            var_name = key.replace("-", "_").lower()
            setattr(self, "_%s__%s" % (self.__class__.__name__, var_name), value)

    def __make_list(self,menu_path,otype):
        rval = []
        for m in menu_path:
            if m[0] not in ["C","D"] and not os.path.isdir(m):
                if m[0]=="N":
                    import clearcase
                    clearcase.start_view_of_path(m)
                if not os.path.isdir(m):
                    self.__warn("%s path not found: %s" % (otype,m))
            else:
                rval.append(os.path.normpath(m))
        return rval

    def __define_args(self):
        # Note :
        # Each long opt will correspond to a variable which can be exploited in the "doit" phase
        # All '-' will be converted to '_' and every upper chars will be lowered
        # Exemple :
        #   My-Super-Opt --> self.__my_super_opt
        #self.__ARG_PARSER.accept_positional_arguments("filenames", "Files to proceed")
        self.__ARG_PARSER.add_argument("database=", "specify database", required=True)
        self.__ARG_PARSER.add_argument("ini-file=","read the file .ini and add dxl menus and dxl addins (default: %s)" % self.__ini_file,required=False, default=self.__ini_file)
        self.__ARG_PARSER.add_argument("extra-directory=[]","scan the specified director(y/ies)",required=False)
        self.__ARG_PARSER.add_argument("scan-file=[]","scan the specified dxl file(s)",required=False)
        self.__ARG_PARSER.add_argument("complete","scan files and all includes from scratch; the last result directory is saved",required=False)
        self.__ARG_PARSER.add_argument("output=","custom location for results directory, default to CODE/DOORS_TOOLS/dxl_scan_result",required=False)

    # not working/blocks. Better use network_specifics.get_memory and check for 0
    #def __still_alive(self):
    #    return self.__doors_process.poll() == None


    def __make_tree(self, root_dir):
        """
            Scan directories, subdirectories and files recursively
            and returns them in a nested dictionnary
        """

        dir_path = {}
        root_dir = root_dir.rstrip(os.sep)
        start = root_dir.rfind(os.sep) + 1

        for path, dirs, files in os.walk(root_dir):
            if path.startswith("K"):
                folders = path[start:].split(os.sep)
                if folders[0] == os.path.basename(root_dir):
                    folders[0] = root_dir

                subdir = {}
                for file in files:
                    subdir[file] = path+os.sep+file

                # Better alternative to reduce(): parent = reduce(dict.get, folders[:-1], dir_path)
                parent = dir_path
                for folder in folders[:-1]:
                    parent = dict.get(parent, folder)

                parent[folders[-1]] = subdir

        return dir_path


    def __make_tree_new(self, root_dir):
        """
            Same as __make_tree but NOT WORKING
        """

        dir_path = {}
        root_dir = root_dir.rstrip(os.sep)
        start = root_dir.rfind(os.sep) + 1

        import find
        import collections
        f = find.Find()
        filelist = f.init(root_dir,type_list=["f"])
        pathdict = collections.OrderedDict()
        for f in filelist:
            path = os.path.dirname(f)
            name = os.path.basename(f)

            the_path = path
            while not the_path in pathdict:
                print the_path
                pathdict[the_path] = []
                the_path = os.path.dirname(the_path).rstrip(os.sep)
                if the_path=="":
                    break
            pathdict[path].append(name)

        for path,files in pathdict.iteritems():
            if path.startswith("K"):
                folders = path[start:].split(os.sep)
                if folders[0] == os.path.basename(root_dir):
                    folders[0] = root_dir

                subdir = {}
                for file in files:
                    subdir[file] = path+os.sep+file

                a = folders[:-1]
                b = dir_path
                print "FFFFFF",a,b
                parent = reduce(dict.get, a, b)
                print parent
                if parent==None:
                    pass
                    #raise Exception("parent = none: ",path,subdir,folders[:-1])
                else:
                    print "PARENT NOT NONE"
                    print parent
                    parent[folders[-1]] = subdir
        return dir_path


    def __save_tree(self, txt_filename, dxl_menu):
        """
            Write nested dictionnaries from make_tree() in
            a list in a txt file
        """

        import time
        start_time = time.time()
        with open(txt_filename,"wb") as f:
            pickle.dump([self.__make_tree(m) for m in dxl_menu],f)
        #print "ELAPSED TIME : ", start_time-time.time()


    def __gen_html(self, dict_obj, file, includes_list):
        """
            Generate HTML tree directory from txt file
        """

        file.write("<ul>")
        for k, v in dict_obj.iteritems():
            if isinstance(v, dict):
                file.write("<li style='list-style-type: none;'><b>&#9492;&#9472; ")
                file.write(k)
                file.write("</b></li>")
                self.__count_dirs += 1
                self.__gen_html(v, file, includes_list)
            else:
                if k.endswith(".dxl"):
                    #check hash first with path
                    html_file = self.__get_hash(v)+"_"+os.path.basename(v)
                    # if executable by DOORS, display file
                    is_exec_by_doors = self.__file_exec_by_doors(v, self.__get_dxl_content(v))

                    if is_exec_by_doors:
                        file.write("<li style='list-style-type: none;'>&#9492;&#9472; <a href='dxl_files/"+html_file.replace(" ","%20")+".html'>")
                        file.write(k.rstrip(".dxl"))
                        file.write("</a></li>")
        file.write("</ul>")


    def __txt2html(self, txt_filename, dxl_includes_list_filename, html_template, dxl_menu):
        """
            Read directories, subdirectories, files and include from txt files
            and call gen_html()
        """

        with open(txt_filename,"rb") as f:
            dict_list = pickle.load(f)

        with open(dxl_includes_list_filename,"rb") as f:
            includes_list = pickle.load(f)

        for path in dxl_menu:
            if os.path.basename(path) == "project":
                dxl_menu = "projects"
            elif os.path.basename(path) == "addins":
                dxl_menu = "addins"
            else:
                dxl_menu = "extra"

        with open(html_template,"w") as f:
            f.write("<!DOCTYPE html><html><font face='consolas' size='2'><head><title>DXL files directory - "+dxl_menu+"</title>")
            f.write(self.__template.get_css())
            f.write("</head><body>")
            f.write(self.__template.get_header())
            for dict in dict_list:
                self.__gen_html(dict, f, includes_list)
            f.write("</body></font></html>")


    def __dict2list(self, dict_obj, dxl_files_list):
        """
            Returns a list of DXL files found in a dictionnary
        """

        for k, v in dict_obj.iteritems():
            if isinstance(v, dict):
                self.__dict2list(v, dxl_files_list)
            else:
                if k.endswith(".dxl"):
                    dxl_files_list.append(v)

        return dxl_files_list


    def __get_dxl_files(self, txt_filename):
        """
            Calls dict2list() to loop over each nested dictionnary
            and returns a list of DXL files
        """

        with open(txt_filename,"rb") as f:
            dict_list = pickle.load(f)

        dxl_files_list = []
        for dict_obj in dict_list:
            dxl_files_list.extend(self.__dict2list(dict_obj,[]))

        return dxl_files_list


    def __get_dxl_content(self, dxl_file):
        """
            Get DXL file content to feed the lexer
        """

        with open(dxl_file) as f:
            data = f.read()

        return data


    def __write_list_files(self, f, embedded):
        """
            Writes an HTML list of files, without header if embedded in homepage
        """

        f.write("<!DOCTYPE html><html><head><title>DXL files</title>")
        f.write("<meta http-equiv='X-UA-Compatible' content='IE=9' />")
        f.write(self.__template.get_css())
        f.write("</head><body style='line-height:1.4; min-width:800px;'>")
        if not embedded:
            f.write(self.__template.get_header())
            f.write("<h1 style='margin-left:20px;'>"+str(len(self.__files_list))+" DXL files from projects and addins</h1>")
        f.write("<div style='margin:20px;'>")
        f.write("<table style='width:100%; background:#FFF;'>")
        f.write("<tr><th>Filename</th><th>Issues</th><th>Includes</th><th>Last analysis</th><th>Lines of code</th></tr>")

        for filename in sorted(self.__hash_file_dict.items(), key=operator.itemgetter(1)):
            file_with_hash = filename[0]
            file_link_to_display = filename[1].replace(".html","")

            """file_content = self.__get_dxl_content(self.__output_dir+"/dxl_files/"+file_with_hash)
            match_nb_lines = re.search("<!--\d*-->",file_content)"""

            try:
                nb_lines = self.__loc_dict[file_with_hash.replace(".html","")]
            except:
                nb_lines = "-"

            """if match_nb_lines != None:
                nb_lines = match_nb_lines.group(0).strip("<!-->")"""

            edit_bat_content = self.__get_dxl_content(self.__output_dir+"/edit_bat/"+file_with_hash.replace(".html","")+".bat")
            match_abs_file_path = re.search("(?=notepad).*",edit_bat_content)
            if match_abs_file_path != None:
                abs_file_path = match_abs_file_path.group(0).lstrip("notepad++ ")

            nb_err = "-"
            if abs_file_path in self.__report.keys():
                nb_err = str(len(self.__report[abs_file_path]))

            nb_inc = "-"
            fh = file_with_hash.replace(".html","")
            if fh in self.__nb_inc_dict.keys():
                nb_inc = self.__nb_inc_dict[fh]

            f.write("<tr id='tr-list'>")
            # display filename without hash and html extension
            link = "dxl_files"+os.sep+file_with_hash
            last_analysis_date = datetime.datetime.fromtimestamp(os.path.getmtime(self.__output_dir+os.sep+link)).strftime("%d/%m/%y - %H:%M")

            f.write("<td><a href='"+link+"'>"+file_link_to_display+"</a></td>")
            f.write("<td>"+str(nb_err)+"</td>")
            f.write("<td>"+str(nb_inc)+"</td>")
            f.write("<td style='min-width:60px;'>"+last_analysis_date+"</td>")
            f.write("<td>"+str(nb_lines)+"</td>")
            f.write("</tr>")

        f.write("</table></div></body></html>")


    def __list_html_files(self):
        """
            Calls write_list_files() twice (embedded and not)
        """

        self.__files_list = os.listdir(self.__output_dir+"/dxl_files")

        self.__hash_file_dict = dict()
        for dxl_file in self.__files_list:
            self.__hash_file_dict[dxl_file] = dxl_file.lstrip(dxl_file[:41])

        with open(self.__output_dir+"/list.html","wb") as f:
            self.__write_list_files(f,embedded=False)

        with open(self.__output_dir+"/embedded_list.html","wb") as f:
            self.__write_list_files(f,embedded=True)


    def __gen_homepage(self):
        """
            Generates HTML homepage with access to directory trees, error reports and list of files
            from template in template.py
        """

        self.homepage = self.__template.get_homepage(self.__log_file_name, self.__count_lines, self.__count_functions, self.__count_files, self.__count_includes, \
                                                     self.__count_dirs, self.__count_issues, self.__last_scan_date, self.__user_tgi, self.__scanned_dirs_list)

        with open(self.__output_dir+"/dxl_scan_home.html","wb") as f:
            f.write(self.homepage)

        with open(self.__output_dir+"/dxl_scan.bat","wb") as f:
            f.write("@echo off")
            f.write("\n")
            f.write("CD /D %~dp0 \n")
            f.write("R:\AMS_afr_A400M\ESPACE_TRAVAIL_COMMON\WP5_SupportMultiLoad\INSTALLS\pypy\pypy.exe dxl_scan.py -i start_doors.ini -d FBL_SSDD")


    def __add_error(self,dxl_file,e):
        """
            Add errors to list
        """

        if dxl_file not in self.__report:
            self.__report[dxl_file] = []
        self.__report[dxl_file].append(e)


    def __get_valid_includes(self ,dxl_file, dxl_content, log_error):
        """
            Validates includes from lexer function
            Outputs to error report and/or HTML version of DXL file
        """

        start_doors_ini_paths = self.__addin_dirs + self.__project_dirs
        exists_path_list = set()

        fs = os.path.getsize(dxl_file)
        if fs>500*1000:
            pass
        else:
            self.__lexer.lexer.lineno = 1
            self.__lexer.get_tokens(dxl_content)
            include_dict = self.__lexer.include_dict

            for path, line in include_dict.iteritems():
                if path.startswith("\\"):
                    path = path.lstrip("\\")
                found = False
                if os.path.isabs(path):
                    # absolute path
                    if os.path.exists(path):
                        exists_path_list.add(path)
                        found = True
                else:
                    # relative path: search in DOORS paths
                    for start_path in start_doors_ini_paths:
                        fp = os.path.join(start_path,path)
                        fp = os.path.normpath(fp)
                        if os.path.exists(fp):
                            exists_path_list.add(fp)
                            found = True
                            break
                        else:
                            doors_includes_path = "D:/AppX64/IBM/Rational/DOORS/9.6/lib/dxl"
                            c_path = os.path.join(doors_includes_path, path)
                            c_path = os.path.normpath(c_path)
                            if os.path.exists(c_path):
                                exists_path_list.add(c_path)
                                found = True
                                break
                if not found:
                    # DOORS relative paths
                    if not path.startswith(("utils","%%Path%%","%%templatePath%%")):
                        if log_error:
                            self.__add_error(dxl_file,IncludeError(path,"Path not found or not valid",line))

            valid_includes_list = []
            for path in exists_path_list:
                t = None
                #if "\\" in path:
                #    t = "backslash"
                if "\\\\" in path:
                    t = "Double Backslash"
                if t != None:
                    if log_error:
                        self.__add_error(dxl_file,IncludeError(path,t,line))

                drive = os.path.splitdrive(path)[0]
                if drive in ["K:","D:"]:
                    valid_includes_list.append(path)
                #R: paths illegal, but allow in valid_includes_list for hyperlink in HTML
                elif drive == "R:":
                    valid_includes_list.append(path)
                    if log_error:
                        self.__add_error(dxl_file,IncludeError(path,"Illegal path",line))
                else:
                    if log_error:
                        self.__add_error(dxl_file,IncludeError(path,"Illegal path",line))

            self.__valid_includes_dict[dxl_file] = valid_includes_list


    def __check_sys_calls(self,dxl_file,dxl_content):
        """
            Outputs system calls from lexer function to error report
        """

        fs = os.path.getsize(dxl_file)
        if fs>500*1000:
            pass
        else:
            self.__lexer.lexer.lineno = 1
            self.__lexer.get_tokens(dxl_content)
            sys_call_dict = self.__lexer.sys_call_dict

            for sys_call, line in sys_call_dict.iteritems():
                self.__add_error(dxl_file,FunctionError(sys_call,"System Call",line))


    def __get_func_declarations(self,dxl_file,dxl_content):
        """
            Gets function names declarations
        """

        func_declarations_dict = dict()
        fs = os.path.getsize(dxl_file)
        if fs>500*1000:
            pass
        else:
            self.__lexer.lexer.lineno = 1
            func_declarations_dict = self.__lexer.get_func_declarations(dxl_content)

        return func_declarations_dict

    """def __get_functions_duplications(self,dxl_file,dxl_content):
        func_declarations_dict = self.__get_func_declarations(dxl_file,dxl_content)

        for func_name,lines_list in func_declarations_dict.items():
                if len(lines_list)>1:
                    self.__add_error(dxl_file,FunctionError(func_name,"Function defined more than once with the same name",str(lines_list).strip('[]')))
    """

    def __get_defined_functions(self,dxl_file,dxl_content):
        """
            Gets defined functions in all files
        """

        if self.__func_declarations_dict:
            for function_def in self.__func_declarations_dict.keys():
                self.__count_functions += 1
                if not function_def in self.__defined_functions_dict:
                    self.__defined_functions_dict[function_def] = []
                self.__defined_functions_dict[function_def].append(dxl_file)


    def __get_called_functions(self,dxl_file,dxl_content):
        """
            Gets called functions in all files
        """

        #called_func_list = self.__lexer.get_called_functions(dxl_content)
        self.__lexer.get_tokens(dxl_content)
        called_func_list = self.__lexer.func_called
        # discriminate DXL builtin functions
        """for called_func in called_func_list:
            if self.__builtin_fcts_dict.has_key(called_func):
                called_func_list.remove(called_func)"""
        self.__called_functions.extend(called_func_list)


    def __get_not_called_functions(self):
        """
            Gets functions in all files in which they are defined but not called
        """

        with open(self.__output_dir+"/report_function_not_called.html","wb") as f:
            f.write("<html><font face='helvetica' size='2'><head><title>Functions not called</title>")
            f.write("<meta http-equiv='X-UA-Compatible' content='IE=8' />")
            f.write(self.__template.get_css())
            f.write("</head><body>")
            f.write(self.__template.get_header())
            f.write("<h1 style='padding-left:30px;'>Functions not called issues</h1>")
            f.write("<ul>")

            for defined_func,dxl_file_list in self.__defined_functions_dict.items():
                dxl_file_list_html = []

                for dxl_file in dxl_file_list:
                    html_file_path = "dxl_files/"+self.__get_hash(dxl_file)+"_"+os.path.basename(dxl_file)+".html"
                    link_html = "<li><a href='"+html_file_path.replace(" ","%20")+"'>"+os.path.normpath(dxl_file)+"</a></li>\n"
                    dxl_file_list_html.append(link_html)

                if not defined_func in self.__called_functions:
                    f.write("<ul>")
                    f.write("Function <b>"+defined_func+"</b> defined but never called in:")
                    for dxl_file in dxl_file_list_html:
                        f.write(dxl_file)
                    f.write("</ul>")
                    f.write("<br>")

            f.write("</ul>")
            f.write("</body></font></html>")

            #if not defined_func in self.__called_functions:
            #    self.__add_error("Function "+defined_func+" defined but never called in",FunctionError(str(dxl_file_list_html).strip("['\n]"),"Function defined but never called",0))


    def __file_exec_by_doors(self,dxl_file,dxl_content):
        """
            Checks if file is executable by DOORS by verifying comments in file
            and filename in the .idx file in the same directory
        """

        is_exec_by_doors = False

        fs = os.path.getsize(dxl_file)
        if fs>500*1000:
            pass
        else:
            self.__lexer.lexer.lineno = 1
            self.__lexer.get_tokens(dxl_content)
            is_exec_by_doors = self.__lexer.is_exec_by_doors

            if self.__extra_directory:
                for extra_dir in self.__extra_directory:
                    if os.path.normpath(dxl_file).startswith(os.path.normpath(extra_dir)):
                        is_exec_by_doors = True

            # check if a .idx file is present in dxl file dir
            file_dir = os.path.dirname(dxl_file)
            list_files = os.listdir(file_dir)

            for filename in list_files:
                if os.path.splitext(filename)[-1] == ".idx":
                    with open(file_dir+os.sep+filename) as f:
                        data = f.read()
                        if os.path.splitext(os.path.basename(dxl_file))[0] in data:
                            is_exec_by_doors = True

        return is_exec_by_doors


    def __check_string_init(self,dxl_file,dxl_content):
        """
            Checks string initialisations arguments
        """

        fs = os.path.getsize(dxl_file)
        if fs>500*1000:
            pass
        else:
            self.__lexer.lexer.lineno = 1
            self.__lexer.get_tokens(dxl_content)
            string_init_dict = self.__lexer.string_init_dict
            string_init_loop_dict = self.__lexer.string_init_loop_dict

            """for line in string_init_loop_dict.values():
                self.__add_error(dxl_file,Error("String initialization","in loop",line))"""

            for token, line in string_init_dict.items():
                if token == "null":
                    self.__add_error(dxl_file,Error("Bad string initialization","Use \"\" instead of null",line))


    def __check_pragmas(self,dxl_file,dxl_content):
        """
            Checks pragma arguments
        """

        self.__is_error_pragma = False
        fs = os.path.getsize(dxl_file)
        if fs>500*1000:
            pass
        else:
            self.__lexer.lexer.lineno = 1
            self.__lexer.get_tokens(dxl_content)
            pragma_dict = self.__lexer.pragma_dict

            # new instance of Lexer needed for getting
            # correct token lines
            lexer = Lexer()
            lexer.build()
            lexer.get_tokens(dxl_content)
            include_dict = self.__lexer.include_dict

            # Check pragmas (defined, before includes, correct args)
            #for include_dict in include_list:
            # if includes found, get line of first include seen
            if include_dict:
                first_include_line = min(include_dict.values())
            # no include in file
            else:
                first_include_line = 0

            #for pragma_dict in self.__pragma_list:
            # if pragma found, get line of last pragma
            if pragma_dict:
                last_pragma_line = max(pragma_dict.values())
            # no pragma in file
            else:
                last_pragma_line = 0

            # if includes and pragma in file
            if first_include_line != 0 and last_pragma_line != 0:
                # if pragma after include => error
                if last_pragma_line > first_include_line:
                    #self.__add_error(dxl_file,PragmaError("Pragma","Must be defined before includes",last_pragma_line))
                    self.__is_error_pragma = True
            # if no pragma
            elif first_include_line != 0 and last_pragma_line == 0:
                pragma_tok = "pragma runLim, 0"
                #self.__add_error(dxl_file,PragmaError(pragma_tok,"Not defined",last_pragma_line))
                self.__is_error_pragma = True

            # check pragma args
            #for pragma_dict in self.__pragma_list:
            for pragma, line in pragma_dict.iteritems():
                if "xflags" in pragma:
                    self.__add_error(dxl_file,PragmaError(pragma,"Pragma xflags forbidden",line))
                elif "runLim" in pragma:
                    exec_cyc = int(pragma.split(",")[1])
                    if exec_cyc != 0:
                        self.__add_error(dxl_file,PragmaError(pragma,"Execution cycle not 0",line))


    def __check_duplicates(self,dxl_file_checking,dxl_files_list):
        """
            Returns duplicate files (same name, whatever content) in a list
        """

        dxl_basename_list = []

        dxl_file_checking_basename = os.path.basename(dxl_file_checking)

        # get dxl files basenames
        for dxl_file in dxl_files_list:
            dxl_file_basename = os.path.basename(dxl_file)
            dxl_basename_list.append(dxl_file_basename)

        # get duplicate file names
        dup_file_list = [k for k,v in collections.Counter(dxl_basename_list).items() if v>1]

        # retrieve abs path of duplicate files
        for dup_file in dup_file_list:
            dup_file_path_list = []
            # find dxl_file with same name
            for dxl_file in dxl_files_list:
                if dup_file == os.path.basename(dxl_file):
                    dup_file_path_list.append(dxl_file)

            # if current dxl_file is in duplicates list
            # return the other duplicate files
            if dxl_file_checking in dup_file_path_list:
                for dup_path in dup_file_path_list:
                    if dup_path != dxl_file_checking:
                        self.__add_error(dxl_file_checking,DuplicateFileError("Same filename",dup_path))


    def __check_same_include_content(self):
        """
            Returns duplicate include (whatever name but same content) from hash_content.txt
        """

        with open(self.__output_dir+"/txt/hash_content.txt","rb") as f:
            hash_content_dict = pickle.load(f)

        hash_content_list = []
        for hash_value in hash_content_dict.values():
            hash_content_list.append(hash_value)

        same_include_hash_list = [k for k,v in collections.Counter(hash_content_list).items() if v>1]

        hash_duplicate_dict = dict()
        for k,v in hash_content_dict.items():
            for same_include_hash in same_include_hash_list:
                if v == same_include_hash:
                    if not v in hash_duplicate_dict:
                        hash_duplicate_dict[v] = []
                    hash_duplicate_dict[v].append(k)

        for v_include_list in hash_duplicate_dict.values():
            for include in v_include_list:

                # format duplicate includes for report
                other_includes_list = v_include_list
                other_includes_list.remove(include)
                include_links_list = []
                for other_include in other_includes_list:
                    include_hash = self.__get_hash(other_include)
                    include_basename = os.path.basename(other_include)
                    link = "dxl_files/"+include_hash+"_"+include_basename+".html"

                    other_include = "<a href='"+link+"'>"+os.path.normpath(other_include)+"</a>"
                    include_links_list.append(other_include)

                self.__add_error(include,DuplicateFileError("Identical content",str(include_links_list).strip("[]").replace("'","")))


    def __check_dependencies(self,dxl_menu,include_dict):
        """
            Inverse lookup from includes_dict
            Returns a new dict with includes as keys and DXL files lists as values
        """

        # Generate html report for dependencies
        with open(self.__output_dir+"/report_dependencies_"+dxl_menu+".html","wb") as f:
            f.write("<html><font face='helvetica' size='2'><head><title>Dependencies in "+dxl_menu+" directories</title>")
            f.write("<meta http-equiv='X-UA-Compatible' content='IE=8' />")
            f.write(self.__template.get_css())
            f.write("</head><body>")
            f.write(self.__template.get_header())
            f.write("<h1 style='padding-left:30px;'>Dependencies</h1>")
            f.write("<ul>")

            for k,v in include_dict.items():
                html_include_file_path = "dxl_files/"+self.__get_hash(k)+"_"+os.path.basename(k)+".html"
                f.write("<br><li><a href='"+html_include_file_path.replace(" ","%20")+"'>"+os.path.normpath(k)+"</a> included in :</li>\n")
                f.write("<ul>")
                for dxl_file in v:
                    html_file_path = "dxl_files/"+self.__get_hash(dxl_file)+"_"+os.path.basename(dxl_file)+".html"
                    f.write("<li><a href='"+html_file_path.replace(" ","%20")+"'>"+os.path.normpath(dxl_file)+"</a></li>\n")
                f.write("</ul>")

            f.write("</ul>")
            f.write("</body></font></html>")


    def __write_list_functions(self,f,report):
        """
            Writes files in which each function is defined, filters if defined more than
            once if report is true
        """

        if report:
            f.write("<html><font face='helvetica' size='2'><head><title>Function duplications in multiples files</title>")
        else:
            f.write("<html><font face='helvetica' size='2'><head><title>Functions defined in DXL files</title>")
        f.write("<meta http-equiv='X-UA-Compatible' content='IE=8' />")
        f.write(self.__template.get_css())
        f.write("</head><body>")
        f.write(self.__template.get_header())
        if report:
            f.write("<h1 style='padding-left:30px;'>Function duplications in multiples files</h1>")
        else:
            f.write("<h1 style='padding-left:30px;'>Functions defined in DXL files</h1>")
        f.write("<ul>")

        for k,v in self.__defined_functions_dict.items():
            if report:
                if len(v) > 1:
                    f.write("<br><li>Function <b>"+k+"</b> defined more than once with the same name in : </li>\n")
                    f.write("<ul>")
                    for dxl_file in v:
                        html_file_path = "dxl_files/"+self.__get_hash(dxl_file)+"_"+os.path.basename(dxl_file)+".html"
                        f.write("<li><a href='"+html_file_path.replace(" ","%20")+"'>"+os.path.normpath(dxl_file)+"</a></li>")
                    f.write("</ul>")
            else:
                f.write("<li><b>"+k+"</b> defined in:</li>")
                f.write("<ul>")
                for dxl_file in v:
                    html_file_path = "dxl_files/"+self.__get_hash(dxl_file)+"_"+os.path.basename(dxl_file)+".html"
                    f.write("<li><a href='"+html_file_path.replace(" ","%20")+"'>"+os.path.normpath(dxl_file)+"</a></li>")
                f.write("</ul>")
        f.write("</ul>")
        f.write("</body></font></html>")


    def __gen_list_functions(self):
        """
            Generates HTML list of functions defined in all files
        """

        with open(self.__output_dir+"/list_functions.html","wb") as f:
            self.__write_list_functions(f,report=False)


    def __report_redefined_functions(self):
        """
            Checks functions with the same name defined in different files
        """

        with open(self.__output_dir+"/report_function_global.html","wb") as f:
            self.__write_list_functions(f,report=True)


    def __syntax_color(self,token_type,token_value):
        """
            Returns HTML color style for the token value in parameter
        """

        res_base_ids = ["AND","BOOL","BREAK","BY","CASE","CHAR","CONST","CONTINUE",\
                    "DEFAULT","DO","ELSE","ELSEIF","ENUM","FOR","IF","IN","INT",\
                    "OR","PRAGMA","REAL","RETURN","SIZEOF","STATIC","STRUCT","SWITCH",\
                    "THEN","UNION","VOID","WHILE","INCLUDE"]

        res_other_ids = ["MODULE","OBJECT","SKIP","BUFFER","TEMPLATE","MODULE_VERSION",\
                         "DATE","LINK","LINK_REF","STREAM","REGEXP","ATTR_DEF","DB","DBE"]

        operators = ["PLUS","MINUS","TIMES","DIVIDE","MOD","NOT","XOR","LSHIFT","RSHIFT",\
                     "LOR","LAND","LNOT","TMPC","LT","LE","GT","GE","EQ","NE","EQUALS",\
                     "TIMESEQUAL","DIVEQUAL","MODEQUAL","PLUSEQUAL","MINUSEQUAL","LSHIFTEQUAL",\
                     "RSHIFTEQUAL","ANDEQUAL","XOREQUAL","OREQUAL","INLINK","OVRLOAD","DEF",\
                     "LPAREN","RPAREN","LBRACKET","RBRACKET","COMMA","PERIOD","SEMICOLON",\
                     "COLON","SQUOTE","DQUOTE"]

        braces = ["{","}"]

        keywords2 = python_lacks.read_file(os.path.join(self.__PROGRAM_DIR,"kw2.txt"),remove_blank_lines=True)
        keywords3 = python_lacks.read_file(os.path.join(self.__PROGRAM_DIR,"kw3.txt"),remove_blank_lines=True)
        keywords4 = python_lacks.read_file(os.path.join(self.__PROGRAM_DIR,"kw4.txt"),remove_blank_lines=True)

        comments = ["C_COMMENT","CPP_COMMENT"]

        literals = ["ICONST","FCONST","CCONST","SCONST"]

        style = "\"color:#000000;\""

        # preprocessing for FUNCTION tokens
        if token_type == "FUNCTION":
            token_value = token_value.split("(")[0]

        if token_type in res_base_ids or token_value in res_base_ids:
            style = "\"color:#0404B5;\""
        elif token_type in operators:
            style = "\"color:#000080;\""
        elif token_type in braces or token_value in braces:
            style = "\"color:#000080;\""
        elif token_type in keywords2 or token_value in keywords2:
            style = "\"color:#0080FF;\""
        elif token_type in keywords3 or token_value in keywords3:
            style = "\"color:#8080FF;\""
        elif token_type in keywords4 or token_value in keywords4:
            style = "\"color:#0000FF;\""
        elif token_type in comments:
            style = "\"color:#008000;\""
        elif token_type in literals:
            style = "\"color:#FF0000;\""

        return style


    def __get_hash(self,string):
        """
            Returns hash of string given in parameter
        """

        sha1 = hashlib.sha1()
        sha1.update(string)
        string_hashed = sha1.hexdigest()

        return string_hashed


    def __hash_file_content(self,dxl_file):
        """
            Store hash content of file in a dict and returns it
        """

        file_content = self.__get_dxl_content(dxl_file)
        hash_content = self.__get_hash(file_content)

        self.__hash_content_dict[dxl_file] = hash_content

        with open(self.__output_dir+"/txt/hash_content.txt","wb") as f:
            pickle.dump(self.__hash_content_dict,f)

        return hash_content


    def __compare_hash_content(self,dxl_file,current_hash):
        """
            Compares hash given in parameter with hash stored in dict
        """

        with open(self.__output_dir+"/txt/hash_content.txt","rb") as f:
            hash_content_dict = pickle.load(f)

        if current_hash == hash_content_dict[dxl_file]:
            return True
        else:
            return False


    def __includes_dxl2html(self,valid_includes_dict,dxl_file):
        """
            Generates HTML version of includes
        """

        def analyse_inc():
            # get include hash content and store it
            self.__hash_file_content(include)

            self.__dxl2html(include,include_content)
            self.__get_valid_includes(include,include_content,log_error=False)
            self.__includes_dxl2html(self.__valid_includes_dict,include)

        try:
            for include in valid_includes_dict[dxl_file]:

                if not include in self.__include_dict:
                    self.__include_dict[include] = []
                self.__include_dict[include].append(dxl_file)

                self.__count_includes += 1
                self.__nb_inc_per_file += 1

                include_basename = self.__get_hash(include)+"_"+os.path.basename(include)
                include_content = self.__get_dxl_content(include)

                # if HTML version of include already generated, verify if the content has
                # changed. If content is different or include not generated, analyse it.
                include_scanned = os.path.exists(self.__output_dir+"\dxl_files"+os.sep+include_basename+".html")

                if self.__complete:
                    analyse_inc()
                else:
                    if include_scanned:
                        current_hash = self.__get_hash(include_content)

                        hash_compare = self.__compare_hash_content(include,current_hash)
                        if hash_compare:
                            continue
                        else:
                            analyse_inc()
                    else:
                        analyse_inc()
        except:
            pass


    def __dxl2html(self,dxl_file,dxl_content):
        """
            Generates HTML version of DXL files
        """

        # hash file path to avoid duplicate files overwrite
        dxl_file_basename = self.__get_hash(dxl_file)+"_"+os.path.basename(dxl_file)

        #batch file for editing with notepad++
        edit_bat = self.__output_dir+"/edit_bat/%s.bat" % dxl_file_basename
        with open(edit_bat,"wb") as f:
            f.write("cleartool checkout -nc %s" % dxl_file)
            f.write("\n")
            f.write("start /min notepad++ %s" % dxl_file)

        #batch file for analysing a single DXL file
        scan_bat = self.__output_dir+"/scan_bat/%s.bat" % dxl_file_basename
        with open(scan_bat,"wb") as f:
            f.write("dxl_scan.py -i start_doors.ini -d FBL-SSDD -s "+dxl_file)

        self.__lexer = Lexer()
        self.__lexer.build()
        self.__lexer.init(dxl_content)

        self.__get_valid_includes(dxl_file,dxl_content,log_error=False)

        lines = sorted(self.__lexer.tok_dict.keys())
        self.__count_lines += len(lines)
        self.__loc_dict[dxl_file_basename] = len(lines)

        with open(self.__output_dir+"/dxl_files/"+dxl_file_basename+".html","wb") as f:
            #f.write("<!--%d-->" % lines[-1])
            f.write("<!DOCTYPE html>")
            f.write("<html><font face='consolas' size='2'><head><title>%s</title>" % os.path.basename(dxl_file))
            f.write('<meta http-equiv="X-UA-Compatible" content="IE=8"/>')
            f.write("</head><body style='margin:0;'>")
            f.write("<div style=\"border:1.5px solid #4B9FD5; padding-left:20px; font-family:helvetica;\">")
            f.write("<p>File: %s - Size: %d bytes" % (os.path.basename(dxl_file),os.path.getsize(dxl_file)))
            f.write(" - <a href=%s>Scan this file</a></p>" % os.path.abspath(scan_bat))

            f.write("<p>Open original DXL file: <a href=\"file:///%s\">%s</a> - " % (drives.fix_subst_path(dxl_file),dxl_file))
            f.write("<a href=%s>Edit file</a></p></div>" % os.path.abspath(edit_bat))
            f.write("<br>\n")

            # width of line numbers div
            #total_lines = lines[-1]+1
            total_lines = dxl_content.count("\n")+1

            if total_lines < 100:
                width_left = "30"
                width_right = "90"
            elif total_lines >= 100 and total_lines < 1000:
                width_left = "35"
                width_right = "90"
            elif total_lines >= 1000 and total_lines < 10000:
                width_left = "40"
                width_right = "89"
            else:
                width_left = "45"
                width_right = "88"

            f.write("<div style=\"width:%spx; float:left; text-align: right; color:#666666; background-color:#E1E1E3; padding-right:5px; margin-right:10px;\">" % width_left)
            #for i in xrange(1,lines[-1]+1):
            for i in xrange(1,total_lines+1):
                f.write(str(i)+"<br>\n")
            f.write("</div>")

            # div for the code
            f.write("<div style='width:"+width_right+"%; float:left; white-space: nowrap;'>")

            previous_token_is_include = False
            previous_token_is_sys_call = False
            previous_token_is_comment = False
            #previous_token_is_function = False
            previous_token_is_string_init = False

            keywords = ["BOOL","CHAR","INT","STRING","REAL","VOID","OBJECT","MODULE","SKIP"]
            previous_token_is_keyword = False

            nb_br_in_comment = 0
            nb_br_after_comment = 0
            real_nb_br_after_comment = 0

            has_loop = False
            in_loop = False
            count_brace = 0

            try:
                for l in xrange(1,lines[-1]+1):

                    if l in self.__lexer.tok_dict:
                        line_toks = self.__lexer.tok_dict[l]

                        token = self.__lexer.Token()
                        current_column = 0
                        for token in line_toks:
                            previous_token_is_sys_call = token.type == "SYS_CALL"

                            nb_space = token.column - current_column
                            if nb_space > 0:
                                if current_column == 0:
                                    f.write("&emsp;"*nb_space*2)
                                else:
                                    f.write("&nbsp;"*nb_space)
                                current_column += nb_space

                            # COMMENTS
                            if previous_token_is_comment and token.type != "FUNCTION":
                                style = self.__syntax_color(token.type,token.value)
                                v = "<span id=%d style=%s>%s</span>" % (token.line,style,token.value)

                            """
                            # VARIABLE NOT INITIALIZED
                            elif token.type == "ERR_INIT_VAR":
                                v = "<span id="+str(token.line)+" style=''>"+"<span style='border-bottom: 1px dotted red;'>"+token.value+"</span> <span style='color:#008000; border: solid 2px #008000; font-family:helvetica'> // DXL Scanner : Variable must be initialized</span></span><br>"
                            """

                            """
                            # MORE THAN ONE INSTRUCTION ON ONE LINE
                            elif token.type == "VAR_SINGLE_LINE":
                                style = self.__syntax_color(token.type,token.value)
                                v = "<span id=%d style=%s><span style='border-bottom: 1px dotted red;'>%s</span> <span style='color:#008000; border: solid 1px #008000; font-family:helvetica'> // DXL Scanner : Use one line per variable or instruction</span></span>" % (token.line,style,token.value)
                            """

                            """
                            # STRING INIT IN LOOP
                            if token.type in ["FOR","WHILE"]:
                                has_loop = True
                            if token.type == "LBRACE" and has_loop:
                                in_loop = True
                                count_brace += 1
                            elif token.type == "RBRACE" and has_loop:
                                count_brace -= 1

                                if count_brace == 0:
                                    in_loop = False
                                    has_loop = False
                            if in_loop:
                                if token.type == "STRING_INIT":
                                    v = "<span id=%d style=%s><span style='background-color:red;'>%s</span></span>" % (token.line,style,token.value)
                            """

                            # INCLUDES
                            if previous_token_is_include:
                                include_link = token.value[1:-1]

                                start_doors_ini_paths = self.__addin_dirs+self.__project_dirs
                                try:
                                    # absolute paths
                                    if include_link in self.__valid_includes_dict[dxl_file]:

                                        html_include_link = self.__get_hash(include_link)+"_"+os.path.basename(include_link)
                                        if os.path.splitdrive(include_link)[0] == "R:":
                                            v = "<span id=%d><a href='%s.html'><span style='background-color:red;'>&lt%s&gt</span></a></span>" % (token.line,html_include_link,include_link)
                                        else:
                                            v = "<span id=%d><a href='%s.html'>&lt%s&gt</a></span>" % (token.line,html_include_link,include_link)
                                    else:
                                        for start_path in start_doors_ini_paths:
                                            abs_include_link = os.path.join(start_path,include_link)

                                            # relative paths
                                            if os.path.normpath(abs_include_link) in self.__valid_includes_dict[dxl_file]:
                                                html_include_link = self.__get_hash(os.path.normpath(abs_include_link))+"_"+os.path.basename(include_link)
                                                v = "<span id=%d><a href='%s.html'>&lt%s&gt</a></span>" % (token.line,html_include_link,include_link)
                                                break
                                            # DOORS include paths
                                            else:
                                                if include_link.startswith("utils"):
                                                    v = "<span id=%d><font color='green'>&lt%s&gt</font></span>" % (token.line,include_link)
                                                elif include_link.startswith(("%%Path%%","%%templatePath%%")):
                                                    v = "<span id=%d><span style='background-color:orange;'>&lt%s&gt</span> <span style='color:#008000; font-family:helvetica'> // DXL Scanner Exception : &#37;&#37;Path&#37;&#37; not interpreted, include should be valid</span></span>" % (token.line,include_link)
                                                else:
                                                    doors_includes_path = "D:/AppX64/IBM/Rational/DOORS/9.6/lib/dxl"
                                                    c_path = os.path.join(doors_includes_path,include_link)
                                                    c_path = os.path.normpath(c_path)
                                                    if os.path.exists(c_path):
                                                        html_include_link = self.__get_hash(os.path.normpath(c_path))+"_"+os.path.basename(include_link)
                                                        v = "<span id=%d><span style='background-color:red;'><a href='%s.html'>&lt%s&gt</a></span> <span style='color:#008000; font-family:helvetica'> // DXL Scanner : path found but not valid</span></span>" % (token.line,html_include_link,include_link)
                                                    else:
                                                        v = "<span id=%d><span style='background-color:red;'>&lt%s&gt</span></span>" % (token.line,include_link)
                                except KeyError:
                                    pass

                            # SYSTEM CALLS
                            elif previous_token_is_sys_call:
                                v = "<span id=%d><span style=\"background-color:orange;\">%s</span></span>" % (token.line,token.value)

                            # STRING INIT
                            elif previous_token_is_string_init:
                                if token.value == "null":
                                    v = "<span id=%d style=%s><span style='border-bottom: 1px dotted red;'>%s</span> <span style='color:#008000; font-family:helvetica'> // DXL Scanner : Bad initialization, use \"\" instead of null</span></span>" % (token.line,style,token.value)
                                else:
                                    v = "<span id=%d style=%s>%s</span>" % (token.line,style,token.value)

                            # PRAGMAS
                            elif token.type == "PRAGMA":
                                if self.__is_error_pragma:
                                    if "runLim, 0" in token.value or "encoding" in token.value or "stack" in token.value:
                                        v = "<span id=%d><span style='background-color:orange;'>%s</span> <span style='color:#008000; font-family:helvetica'> // DXL Scanner Exception : Pragma is OK</span></span>" % (token.line,token.value)
                                    else:
                                        v = "<span id=%d><span style='background-color:red;'>%s</span></span>" % (token.line,token.value)
                                else:
                                    style = self.__syntax_color(token.type,token.value)
                                    v = "<span id=%d style=%s>%s</span>" % (token.line,style,token.value)

                            # FUNCTION CALLS
                            elif token.type == "FUNCTION" and not previous_token_is_keyword:
                                style = self.__syntax_color(token.type,token.value)
                                func_called = token.value.split("(")[0].rstrip(" ")

                                if self.__func_declarations_dict.has_key(func_called):
                                    # only a unique declared function => one int in value (type list) of func_declarations_dict
                                    if len(self.__func_declarations_dict[func_called]) == 1:
                                        func_def_line = self.__func_declarations_dict[func_called][0] # first item
                                        v = "<span id=%d><span style=%s><a href=#%d>%s</a></span>(%s</span>" %(token.line,style,func_def_line,token.value.split("(",1)[0],token.value.split("(",1)[-1])
                                    else:
                                        v = "<span id=%d><span style=%s>%s</span></span>" % (token.line,style,token.value)

                                elif self.__builtin_fcts_dict.has_key(func_called):
                                    # get DXL builtin functions and redirect to help manual
                                    doors_help_pdf = "R:\AMS_afr_A400M\ESPACE_TRAVAIL_COMMON\WP5_SupportMultiLoad\DOC\DOORS\dxl_reference_manual_96.pdf"
                                    func_def_line = self.__builtin_fcts_dict[func_called]
                                    v = "<span id=%d><span style=%s><a href=file:///%s#page=%d>%s</a></span>(%s</span>" % (token.line,style,doors_help_pdf,func_def_line,token.value.split("(",1)[0],token.value.split("(",1)[-1])

                                else:
                                    v = "<span id=%d><span style=%s>%s</span>(%s</span>" % (token.line,style,token.value.split("(",1)[0],token.value.split("(",1)[1])
                                    #look for the function declaration in the includes
                                    for include in self.__valid_includes_dict[dxl_file]:
                                        include_content = self.__get_dxl_content(include)
                                        func_def_dict = self.__get_func_declarations(include,include_content)

                                        if func_def_dict.has_key(func_called):
                                            # include where the function is defined
                                            html_include_link = self.__get_hash(include)+"_"+os.path.basename(include).replace(os.sep,"/")
                                            # line in the file of function definition
                                            line = func_def_dict[func_called][0]

                                            v = "<span id=%d><span style=%s><a href='%s.html#%d'>%s</a></span>(%s</span>" % (token.line,style,html_include_link,line,token.value.split("(",1)[0],token.value.split("(",1)[-1])

                                            break
                                        else:
                                            #function called but not defined in the same file
                                            v = "<span id=%d><span style=%s>%s</span>(%s</span>" % (token.line,style,token.value.split("(",1)[0],token.value.split("(",1)[-1])

                            else:
                                style = self.__syntax_color(token.type,token.value)
                                v = "<span id=%d style=%s>%s</span>" % (token.line,style,token.value)

                            previous_token_is_include = token.type == "INCLUDE"
                            previous_token_is_comment = token.type == "C_COMMENT"
                            #previous_token_is_function = token.type == "NESTEDCODE"
                            previous_token_is_keyword = token.type in keywords
                            previous_token_is_string_init = token.type == "STRING_INIT"

                            f.write(v)
                            current_column += len(token.value)

                    # Get same format in the html and dxl versions
                    # because lines are counted in C_COMMENT token
                    if previous_token_is_comment:
                        # if 2 following c type comments in the file
                        try:
                            if token.line != actual_line:
                                nb_br_after_comment = 0
                        except UnboundLocalError:
                            pass

                        actual_line = token.line

                        """
                        Offset lines for a correct HTML display

                        nb_br_in_comment : number of <br> in comments
                        nb_br_after_comment: number of <br> from the beginning of the comment
                                             to the first following line of code
                        real_nb_br_after_comment: output wanted to get a consistent style

                        EXEMPLE :
                                nb_br_after_comment:
                            /*      1
                                    2 --> nb_br_in_comment = 2
                            */      3
                                    4 --> real_nb_br_after_comment = 1
                            pragma runLim, 0

                         nb_br_after_comment = 4
                         nb_br_in_comment = 2
                         => real_nb_br_after_comment = 1
                        """
                        nb_br_after_comment +=1
                        nb_br_in_comment = token.value.count("<br>")
                        real_nb_br_after_comment = nb_br_after_comment - nb_br_in_comment - 1
                        if real_nb_br_after_comment > 0:
                            n = real_nb_br_after_comment
                            try:
                                f.write("<br>\n"*(n/n))
                            except IndexError:
                                pass
                        elif real_nb_br_after_comment == 0:
                            f.write("<br>\n")
                    else:
                        f.write("<br>\n")

                f.write("</div></body></font></html>")
            except IndexError:
                pass


    def __make_log_file(self,dxl_file):
        """
            Outputs log file
        """

        self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - "+dxl_file+"\n")


    def __new_vars(self):
        """
            Init required dictionnaries and variables before __check_files()
        """

        self.__report = dict()
        self.__valid_includes_list = []
        self.__valid_includes_dict = dict()
        self.__hash_content_dict = dict()
        self.__defined_functions_dict = dict()
        self.__global_defined_functions = dict()
        self.__called_functions = []
        self.__include_dict = dict()
        self.__nb_inc_dict = dict()
        self.__checked_includes = []

        # stat counters
        self.__count_lines = 0
        self.__count_functions = 0
        self.__count_issues = 0
        self.__count_files = 0
        self.__count_includes = 0
        self.__count_dirs = 0
        self.__last_scan_date = datetime.datetime.now().strftime("%d/%m/%y - %H:%M")
        self.__scanned_dirs_list = []
        self.__loc_dict = dict()


    def __check_files(self,txt_filename):
        """
            Applies previous function to each DXL file and include

            Gets DXL files from dict_list
            dxl_files_list contains all DXL files found in {project,addins}_list.txt
            or a list of files to scan from the command line
        """

        if self.__scan_file:
            dxl_files_list = self.__scan_file
        else:
            dxl_files_list = self.__get_dxl_files(txt_filename)

        tpb = text_progress_bar.TextProgressBar(len(dxl_files_list))

        with open("builtin_functions.txt","rb") as f:
            self.__builtin_fcts_dict = pickle.load(f)

        for dxl_file in dxl_files_list:

            self.__count_files += 1
            self.__nb_inc_per_file = 0

            fs = os.path.getsize(dxl_file)
            if fs>500*1000:
                self.__add_error(dxl_file,OversizeFileError("File (%d bytes) too big" % fs))
            else:
                # output log file
                self.__make_log_file(dxl_file)

                tpb.progress(current_object=os.path.basename(dxl_file)+" (%d bytes)" % os.path.getsize(dxl_file))

                self.__report[dxl_file] = []

                # Get content of each dxl file
                dxl_content = self.__get_dxl_content(dxl_file)

                self.__lexer = Lexer()
                self.__lexer.build()
                self.__lexer.init(dxl_content)

                #------------------------------------------------------------------
                # CHECKS for DXL files

                # Get includes from dxl file and test if valid
                self.__get_valid_includes(dxl_file,dxl_content,log_error=True)
                self.__valid_includes_list.append(self.__valid_includes_dict)

                # String initializations
                self.__check_string_init(dxl_file,dxl_content)

                # System calls
                self.__check_sys_calls(dxl_file,dxl_content)

                # Pragmas
                self.__check_pragmas(dxl_file,dxl_content)

                # Duplicate files
                self.__check_duplicates(dxl_file,dxl_files_list)

                # Comment for DXL to be executed by DOORS
                #self.__is_exec_by_doors = self.__file_exec_by_doors(dxl_file,dxl_content)

                # Functions with the same name in different files
                self.__func_declarations_dict = self.__get_func_declarations(dxl_file,dxl_content)
                #self.__get_functions_duplications(dxl_file,dxl_content)
                self.__get_defined_functions(dxl_file,dxl_content)
                self.__get_called_functions(dxl_file,dxl_content)

                self.__count_issues += len(self.__report[dxl_file])

                #------------------------------------------------------------------
                # CHECKS for includes
                for include in self.__valid_includes_dict[dxl_file]:
                    if include not in self.__checked_includes:
                        self.__checked_includes.append(include)
                        include_content = self.__get_dxl_content(include)
                        self.__lexer.get_tokens(include_content)

                        self.__check_string_init(include,include_content)
                        self.__check_sys_calls(include,include_content)
                        self.__check_pragmas(include,include_content)
                        #self.__func_declarations_dict = self.__get_func_declarations(include,include_content)
                        #self.__get_defined_functions(include,include_content)
                        #self.__get_called_functions(include,include_content)

                #------------------------------------------------------------------
                # Generate HTML version of each DXL file
                self.__dxl2html(dxl_file,dxl_content)

                # get includes recursively for dxl file
                self.__includes_dxl2html(self.__valid_includes_dict,dxl_file)

                # Get number of includes for each main file
                dxl_hash = self.__get_hash(dxl_file)+"_"+os.path.basename(dxl_file)
                self.__nb_inc_dict[dxl_hash] = self.__nb_inc_per_file

        tpb.end()

        # Global Checks
        #------------------------------------------------------------------
        # Report for defined but not called functions
        self.__get_not_called_functions()

        # Generate report for function duplications in files
        self.__report_redefined_functions()

        # Identify from hash_content.txt includes with same content
        self.__check_same_include_content()

        # Make a list of all defined functions
        self.__gen_list_functions()

        # Generate report for dependencies
        # Identify in which files are included .inc files
        if txt_filename == self.__projects_list:
            dxl_menu = "projects"
        elif txt_filename == self.__addins_list:
            dxl_menu = "addins"
        elif txt_filename == self.__extra_list:
            dxl_menu = "extra"

        self.__check_dependencies(dxl_menu,self.__include_dict)


    def __gen_report(self):
        """
            Generates HTML error report
        """

        with open(self.__output_dir+"/report.html","wb") as f:
            f.write("<html><font face=\"helvetica\" size=\"2\"><head><title>Issues report</title>")
            f.write("<meta http-equiv='X-UA-Compatible' content='IE=8'/>")
            f.write(self.__template.get_css())
            f.write("</head><body>")
            ks = sorted(self.__report.keys())
            f.write(self.__template.get_header())
            f.write("<h1 style='padding-left:30px;'>Issues Report</h1>")
            f.write("<ul>")
            for k in ks:
                el = self.__report[k]

                html_file_path = "dxl_files/"+self.__get_hash(k)+"_"+os.path.basename(k)+".html"

                if el:
                    f.write("<br><br>")
                    nb_err = len(el)
                    f.write("<b><font color=\"red\">"+str(nb_err)+" found</font> in "+"<a href='"+html_file_path.replace(" ","%20")+"'>"+k+"</a></b>")
                for e in el:
                    f.write("<li>"+str(e)+os.linesep)
                    # get error line
                    match = re.search("at line \d*",str(e))
                    if match != None:
                        pattern = match.group(0)
                        error_line = re.split("at line ",pattern)[-1]

                        f.write("<a href='"+html_file_path.replace(" ","%20")+"#"+error_line+"'>Go to error</a>")
                        f.write("</li>")
            f.write("</ul>")
            f.write("</body></font></html>")


    def __gen_report_category(self,category):
        """
            Generates HTML error report for each category
        """

        with open(self.__output_dir+"/report_"+category+".html","wb") as f:
            f.write("<html><font face=\"helvetica\" size=\"2\"><head><title>"+category.capitalize()+" issues</title>")
            f.write("<meta http-equiv='X-UA-Compatible' content='IE=8' />")
            f.write(self.__template.get_css())
            f.write("</head><body>")
            f.write(self.__template.get_header())
            f.write("<h1 style='padding-left:30px;'>"+category.capitalize()+" issues</h1>")
            f.write("<ul>")

            ks = sorted(self.__report.keys())
            for k in ks:
                el = self.__report[k]

                html_file_path = "dxl_files/"+self.__get_hash(k)+"_"+os.path.basename(k)+".html"

                # filter errors
                el_category = []

                if category == "include":
                    cat_pattern = "when including"
                elif category == "pragma":
                    cat_pattern = "[pP]ragma|Execution cycle"
                elif category == "system":
                    cat_pattern = "System Call"
                elif category == "duplication":
                    cat_pattern = "Same filename"
                elif category == "function":
                    cat_pattern = "Function defined more than once with the same name"
                elif category == "include duplication":
                    cat_pattern = "Identical content"
                elif category == "string initialization":
                    cat_pattern = "[Ss]tring initialization"

                for e in el:
                    cat_match = re.search(cat_pattern,str(e))
                    if cat_match:
                        el_category.append(e)

                if el_category:
                    f.write("<br><br>")
                    f.write("<b><a href='"+html_file_path.replace(" ","%20")+"'>"+k+"</a></b>")

                for e in el_category:
                    f.write("<li>"+str(e)+os.linesep)
                    match = re.search("at line \d*",str(e))
                    if match != None:
                        pattern = match.group(0)
                        error_line = re.split("at line ",pattern)[-1]

                        f.write("<a href='"+html_file_path.replace(" ","%20")+"#"+error_line+"'>Go to error</a>")
                        f.write("</li>")

            f.write("</ul>")
            f.write("</body></font></html>")


    def __gen_cpd_bat(self):
        """
            Generates batch file for code duplication checks
        """

        with open("dxl_cpd_runner.bat","wb") as f:
            f.write("@echo off\n\n")
            f.write("CD /D %~dp0\n\n")

            path_dir_list = []
            for d in [self.__projects_list,self.__addins_list,self.__extra_list]:
                if os.path.exists(d):
                    if d == self.__projects_list:
                        path_dir_list.append(self.__project_dirs)
                    elif d == self.__addins_list:
                        path_dir_list.append(self.__addin_dirs)
                    elif d == self.__extra_list:
                        path_dir_list.append(self.__extra_dirs)
            for path_dir in path_dir_list:
                    for path in path_dir:
                        # avoid this particular path as it crashes (too many files)
                        if not path == r"K:\CODE\DOORS_TOOLS\PROD":
                            path_mod = path.replace(":","").replace("\\","_")
                            f.write("java -Xmx1024m -classpath cpd/bin net.sourceforge.pmd.cpd.CPD --minimum-tokens 20")
                            f.write(" --files "+path)
                            f.write(" --language dxl --skip-lexical-errors --skip-duplicate-files --format xml --encoding utf-8 > cpd/cpd_"+path_mod+".xml\n\n")


    def __gen_cpd_report(self):
        """
            Generates reports for code duplication
        """

        with open(self.__output_dir+"/report_cpd.html","wb") as f:
            f.write("<html><font face=\"helvetica\" size=\"2\"><head><title>CPD reports</title>")
            f.write("<meta http-equiv='X-UA-Compatible' content='IE=8' />")
            f.write(self.__template.get_css())
            f.write("</head><body>")
            f.write(self.__template.get_header())
            f.write("<h1 style='padding-left:30px;'>CPD reports for each directory</h1>")
            f.write("<ul style='line-height:1.5 !important; font-size:15px;'>Code duplications in :<br><br>")
            path_dir_list = []
            for d in [self.__projects_list, self.__addins_list, self.__extra_list]:
                if os.path.exists(d):
                    if d == self.__projects_list:
                        path_dir_list.append(self.__project_dirs)
                    elif d == self.__addins_list:
                        path_dir_list.append(self.__addin_dirs)
                    elif d == self.__extra_list:
                        path_dir_list.append(self.__extra_dirs)
            for path_dir in path_dir_list:
                for path in path_dir:
                    # this path is not entirely analyzed so don't show it and only show
                    # reports that contains duplications (< 1KB => 0 duplications)
                    if not path == "K:\CODE\DOORS_TOOLS\PROD":
                        report_path = "cpd/"+"cpd_"+path.replace(":","").replace("\\","_")+".xml"
                        report_size = os.path.getsize(report_path)
                        if report_size > 1024:
                            path_link = "../"+report_path
                            f.write("<li style='margin-left:20px;'><a href="+path_link+">"+path+"</a></li>")
            f.write("</ul>")
            f.write("</body></font></html>")


    def __doit(self):
        port_number = "" #Port number of database
        projects_menu_path = []
        addins_menu_path = []

        #Read the admin mode
        import conf_launcher
        cl = conf_launcher.ConfLauncher()

        ini_file_path = project_config.get_configuration_file(self.__ini_file,directory=os.path.join(self.__PROGRAM_DIR,"config"))

        self.__message("Using config file %s" % ini_file_path)
        cl.read_configuration(ini_file_path)

        #Config server and port_number
        ditems = self.__database.split("@")
        port_name = ditems[0].upper()

        admin = True
        #Add parameters of config file
        for prefix in [port_name,"GLOBAL"]:
            pmp = cl.params_of_section(prefix+"_PROJECTS",admin=admin)
            projects_menu_path.extend(pmp)
            amp = cl.params_of_section(prefix+"_ADDINS",admin=admin)
            addins_menu_path.extend(amp)

        # Avoid analyzing and writing errors twice.
        if "K:\\CODE\\DOORS_TOOLS\\PROD" in addins_menu_path:
            try:
                project_menu_path.remove("K:\\CODE\\DOORS_TOOLS\\PROD\\OTHER\\Project")
                addins_menu_path.remove("K:\\CODE\\DOORS_TOOLS\\PROD\\COMMON\\LIB\\DOORS_9")
                addins_menu_path.remove("K:\\CODE\\DOORS_TOOLS\\PROD\\PTO")
            except:
                pass

        uinfo = network_specifics.get_user_infos()
        self.__user_tgi = uinfo.id+" ("+uinfo.get_fullname()+")"
        self.__template = Template()

        now = datetime.datetime.now()
        today_date = now.strftime("%m%d")
        complete_date = now.strftime("_%m%d_%H%M%S")

        if self.__output:
            self.__output_dir = self.__output
        else:
            self.__output_dir = "dxl_scan_result"
            self.__message("No output directory defined. Defaulting to "+os.getcwd()+os.sep+"dxl_scan_result")

        """if self.__complete and os.path.exists(self.__output_dir):
            self.__message("Renamed "+os.path.basename(self.__output_dir)+" --> "+os.path.basename(self.__output_dir)+complete_date+"/")
            os.rename(self.__output_dir,self.__output_dir+complete_date)"""

        #create script dirs
        if not os.path.exists(self.__output_dir):
            os.mkdir(self.__output_dir)
            dirs = ["logs","txt","edit_bat","dxl_files","scan_bat"]
            for d in dirs:
                os.mkdir(self.__output_dir+os.sep+d)

        #-----------------------------------------------------------------------------------------------------
        #Get dxl menus
        self.__project_dirs = self.__make_list(projects_menu_path,"projects")
        self.__addin_dirs = self.__make_list(addins_menu_path,"addins")
        self.__extra_dirs = self.__make_list(self.__extra_directory,"extra")

        #-----------------------------------------------------------------------------------------------------
        #Paths to txt files
        self.__projects_list = self.__output_dir+"/txt/projects_list.txt"
        self.__addins_list = self.__output_dir+"/txt/addins_list.txt"
        self.__extra_list = self.__output_dir+"/txt/extra_list.txt"

        self.__projects_includes_list = self.__output_dir+"/txt/projects_includes_list.txt"
        self.__addins_includes_list = self.__output_dir+"/txt/addins_includes_list.txt"
        self.__extra_includes_list = self.__output_dir+"/txt/extra_includes_list.txt"

        self.__projects_tree = self.__output_dir+"/projects_tree.html"
        self.__addins_tree = self.__output_dir+"/addins_tree.html"
        self.__extra_tree = self.__output_dir+"/extra_tree.html"

        #-----------------------------------------------------------------------------------------------------
        # log file initialization

        log_dir = "logs/"+today_date
        if not os.path.exists(self.__output_dir+os.sep+log_dir):
            os.mkdir(self.__output_dir+os.sep+log_dir)
        self.__log_file_name = os.path.join(log_dir,"log"+complete_date+".txt")
        self.__log_file = open(self.__output_dir+os.sep+self.__log_file_name,"wb")
        self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S - %d/%m/%y")+" - DXL Scanner : scan launched by "+ self.__user_tgi +"\n")

        self.__report = dict()

        if self.__scan_file:
            self.__message("Checking file(s)...")
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Checking file(s)\n")
            self.__new_vars()
            self.__check_files(self.__scan_file)
            projects_files_includes_list = self.__valid_includes_list
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Done checking file(s)\n")

        elif self.__extra_directory:
            # extra directory added in args
            self.__new_vars()

            self.__extra_dirs = self.__make_list(self.__extra_directory,"extra")
            self.__save_tree(self.__extra_list,self.__extra_dirs)
            self.__check_files(self.__extra_list)
            extra_files_includes_list = self.__valid_includes_list

            with open(self.__extra_includes_list,"wb") as f:
                pickle.dump(extra_files_includes_list,f)

            self.__txt2html(self.__extra_list,self.__extra_includes_list,self.__extra_tree,self.__extra_dirs)

        else:
            #-----------------------------------------------------------------------------------------------------
            #Write tree directory of .dxl files folders
            self.__message("Building projects tree directory...")
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Building projects tree directory from "+str(self.__project_dirs)+"\n")
            self.__save_tree(self.__projects_list,self.__project_dirs)
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Done building projects tree directory\n")

            self.__message("Building addins tree directory...")
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Building addins tree directory from "+str(self.__addin_dirs)+"\n")
            self.__save_tree(self.__addins_list,self.__addin_dirs)
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Done building addins tree directory\n")

            #-----------------------------------------------------------------------------------------------------
            #Check rules in projects and addins files
            self.__new_vars()

            self.__message("Checking files for projects...")
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Checking files for projects\n")
            self.__check_files(self.__projects_list)
            projects_files_includes_list = self.__valid_includes_list
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Done checking files for projects\n")

            with open(self.__projects_includes_list,"wb") as f:
                pickle.dump(projects_files_includes_list,f)

            self.__message("Checking files for addins...")
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Checking files for addins\n")
            self.__check_files(self.__addins_list)
            addins_files_includes_list = self.__valid_includes_list
            self.__log_file.write(datetime.datetime.now().strftime("%H:%M:%S")+" - Done checking files for addins\n")

            with open(self.__addins_includes_list,"wb") as f:
                pickle.dump(addins_files_includes_list,f)

            #-----------------------------------------------------------------------------------------------------
            #Get tree directory and generate HTML template
            self.__txt2html(self.__projects_list,self.__projects_includes_list,self.__projects_tree,self.__project_dirs)
            self.__txt2html(self.__addins_list,self.__addins_includes_list,self.__addins_tree,self.__addin_dirs)

            #-----------------------------------------------------------------------------------------------------
            # CPD check
            self.__gen_cpd_bat()
            self.__message("Starting CPD for code duplication check...")
            os.system("dxl_cpd_runner.bat")
            self.__gen_cpd_report()

            # check which directories have been scanned
            dirs = [self.__projects_list,self.__addins_list,self.__extra_list]
            for dir_file in dirs:
                if os.path.exists(dir_file):
                    if dir_file is self.__projects_list:
                        d = "Projects"
                    elif dir_file is self.__addins_list:
                        d = "Addins"
                    elif dir_file is self.__extra_list:
                        d = "Extra directory"

                    self.__scanned_dirs_list.append(d)

            """#Write report for errors found
            f = open("report.txt","wb")
            ks = sorted(self.__report.keys())
            for k in ks:
                el = self.__report[k]
                for e in el:
                    f.write(k+": "+str(e)+os.linesep)
            f.close()"""

            # Generate html homepage with script bat file
            #if not os.path.exists("dxl_scan_home.html"):
            self.__gen_homepage()

            # generate html version of error report
            self.__message("Generating error reports...")
            self.__gen_report()
            # generate reports for each type of error
            categories = ["pragma","include","system","duplication","function","include duplication","string initialization"]
            for category in categories:
                self.__gen_report_category(category)

            # list html generated files
            self.__message("Generating files list...")
            self.__list_html_files()

        self.__log_file.close()

if __name__ == '__main__':
    """
        Description :
            Main application body
    """

    o = StartDoors()
    o._init_from_sys_args()
    #o.init("output_file")
