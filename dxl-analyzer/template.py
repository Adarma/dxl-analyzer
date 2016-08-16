class Template:
    def __init__(self):
        self.log_file_name = "log.txt"
        self.count_lines = 0
        self.count_functions = 0
        self.count_files = 0
        self.count_includes = 0
        self.count_dirs = 0
        self.count_issues = 0
        self.last_scan_date = "00/00/00 - 00:00"
        self.user_tgi = "t000000"
        self.scanned_dirs_list = []

    def get_css(self):
        self.css = '<style>\
            			.main-header a:link{color:white; background-color:transparent; text-decoration:none}\
            			.main-header a:visited {color:white; background-color:transparent; text-decoration:none}\
            			.main-header a:hover {color:white; background-color:#4B9FD5; text-decoration:none;}\
            			.main-header a:active {color:white; background-color:#4B9FD5; text-decoration:none}\
            			.main-header a{display:block;}\
            			\
                        #list-li a:link{text-decoration:none};\
                        \
            			* {\
            				box-sizing: border-box;\
            			}\
            			body {\
            				background: #F0F0F0;\
            				margin: 0;\
                            margin-bottom: 10px;\
            				font-family: sans-serif;\
            				line-height: 1.2;\
            			}\
            			.main-header ul {\
            				list-style: none;\
            				padding: 0;\
            				margin: 0;\
            			}\
            			.main-header {\
                            font-family: helvetica;\
            				width: 100%;\
            				background-color:#383838;\
            				font-size:14px;\
            			}\
            			\
            			.main-header:after {\
            				content: " ";\
            				display: table;\
            				clear: both;\
            			}\
            			.main-nav, .drop-nav {\
            				background: #383838;\
            			}\
            			.main-nav {\
            				float: left;\
            				border-radius: 4px;\
            			}\
            			.main-nav > li {\
            				float: left;\
            				border-left: solid 1px #383838;\
            			}\
            			.main-nav li:first-child {\
            				border-left: none;\
            			}\
            			.main-nav a {\
            				color: #FFF;\
            				display: block;\
            				padding: 5px 10px;\
            				text-decoration: none;\
            			}\
            			.dropdown, .flyout {\
            				position: relative;\
            			}\
            			.dropdown:after {\
            				display: block;\
            				position: absolute;\
            				top: 38%;\
            				right: 50%;\
            			}\
            			.flyout-nav {\
            				position: absolute;\
            				display: none;\
            				width: 120%;\
            			}\
            			.drop-nav {\
            				background: #383838;\
            				position: absolute;\
            				display: none;\
            				width: 200%;\
            			}\
            			\
            			.dropdown:hover > .drop-nav,\
            			.flyout:hover > .flyout-nav {\
            				display: block;\
            			}\
            			.flyout-nav {\
            				background: #383838;\
            				left: 100%;\
            				top: 0;\
            			}\
            			.flyout-nav li:hover a {\
            				background: #4B9FD5;\
            			}\
                        #list-ul {\
                            list-style-type: none;\
                            margin:0;\
                            padding:0px;\
                            border:1px solid #000;\
                        }\
                        #tr-list:nth-child(odd) {\
                            background: #DBDBDB !important;\
                        }\
                        #list-li {\
                            padding-left:15px;\
                        }\
                        table {\
                            border:1px solid #000;\
                        }\
                        th {\
                            border:1px solid #000;\
                            text-align:left;\
                            padding-left:15px;\
                        }\
                        td {\
                            border:1px solid #000;\
                            margin:0;\
                            padding-bottom:5px;\
                            padding-top:5px;\
                            padding-left:15px;\
                            padding-right:10px;\
                        }\
            		</style>'

        return self.css

    def get_header(self):
        self.header = '<div class="main-header">\
     			        \
            				<ul class="main-nav">\
            					<li><a href="dxl_scan_home.html">Home</a></li>\
            					<li class="dropdown">\
            						<a href="#">Menus &#9662;</a>\
            						<ul class="drop-nav">\
            							<li><a href="projects_tree.html">Projects</a></li>\
            							<li><a href="addins_tree.html">Addins</a></li>\
            							<li><a href="extra_tree.html">Extras</a></li>\
            						</ul>\
            					</li>\
                                \
            					<li><a href="report.html">Issues</a></li>\
            					<li><a href="dxl_scan.bat">Start scan script</a></li>\
            				</ul>\
            		          \
            				<!--<span><a href="dxl_scan_home.html" style="color:white">Home</a></span>\
            				<span style="padding-left:10px;">Menus</span>\
            				<span style="padding-left:10px">Issues</span>\
            				<span style="position:absolute; right:20px;"><a href="dxl_scan.bat" style="color:white;">Start scan script</a></span>-->\
                            \
            		</div>'

        return self.header

    def get_homepage(self,log_file_name,count_lines,count_functions,count_files,count_includes,count_dirs,count_issues,last_scan_date,user_tgi,scanned_dirs_list):
        self.homepage = '<!DOCTYPE HTML>\
            <html><font face="helvetica" size="2">\
            	\
            	<head>\
                    <meta http-equiv="X-UA-Compatible" content="IE=9" />\
            		<title>DXL Scanner</title>\
                    \
            		<style>\
            			a:link{color:black; background-color:transparent; text-decoration:none}\
            			a:visited {color:black; background-color:transparent; text-decoration:none}\
            			a:hover {color:white; background-color:#4B9FD5; text-decoration:none;}\
            			a:active {color:white; background-color:#4B9FD5; text-decoration:none}\
            			a{display:block;}\
            			\
            			#col a:link{color:#4B9FD5; background-color:transparent; text-decoration:underline}\
            			#col a:visited {color:#4B9FD5; background-color:transparent; text-decoration:underline}\
            			#col a:hover {color:#CAE3F2; background-color:transparent; text-decoration:underline}\
            			#col a:active {color:#CAE3F2; background-color:transparent; text-decoration:underline}\
            			#col a{display:block; font-size:20px;}\
                        \
            			* {\
            				box-sizing: border-box;\
            			}\
            			body {\
            				background: #F0F0F0;\
            				margin: 0;\
            				font-family: sans-serif;\
            				line-height: 1.2;\
            			}\
            			ul {\
            				list-style: none;\
            				padding: 0;\
            				margin: 0;\
            			}\
            			.main-header {\
            				width: 100%;\
            				background-color:#383838;\
            				font-size:14px;\
            			}\
            			\
            			.main-header:after {\
            				content: " ";\
            				display: table;\
            				clear: both;\
            			}\
            			.main-nav, .drop-nav {\
            				background: #383838;\
            			}\
            			.main-nav {\
            				float: left;\
            				border-radius: 4px;\
            			}\
            			.main-nav > li {\
            				float: left;\
            				border-left: solid 1px #383838;\
            			}\
            			.main-nav li:first-child {\
            				border-left: none;\
            			}\
            			.main-nav a {\
            				color: #FFF;\
            				display: block;\
            				padding: 5px 10px;\
            				text-decoration: none;\
            			}\
            			.dropdown, .flyout {\
            				position: relative;\
            			}\
            			.dropdown:after {\
            				display: block;\
            				position: absolute;\
            				top: 38%;\
            				right: 50%;\
            			}\
            			.flyout-nav {\
            				position: absolute;\
            				display: none;\
            				width: 120%;\
            			}\
            			.drop-nav {\
            				background: #383838;\
            				position: absolute;\
            				display: none;\
            				width: 200%;\
            			}\
            			\
            			.dropdown:hover > .drop-nav,\
            			.flyout:hover > .flyout-nav {\
            				display: block;\
            			}\
            			.flyout-nav {\
            				background: #383838;\
            				left: 100%;\
            				top: 0;\
            			}\
            			.flyout-nav li:hover a {\
            				background: #4B9FD5;\
            			}\
            			\
            		</style>\
            	</head>\
                \
            	<body>\
            		<div class="main-header">\
            			\
            				<ul class="main-nav">\
            					<li><a href="dxl_scan_home.html">Home</a></li>\
            					<li class="dropdown">\
            						<a href="#">Menus &#9662;</a>\
            						<ul class="drop-nav">\
            							<li><a href="projects_tree.html">Projects</a></li>\
            							<li><a href="addins_tree.html">Addins</a></li>\
            							<li><a href="extra_tree.html">Extras</a></li>\
            						</ul>\
            					</li>\
                                \
            					<li><a href="report.html">Issues</a></li>\
            					<li><a href="dxl_scan.bat">Start scan script</a></li>\
            				</ul>\
            		\
            		</div>\
            		<div>\
            			<div style="border:2px solid #4B9FD5; border-top:none; width:175px; background-color:#CAE3F2; float:left;">\
            				<h3 style="font-size:20px; padding-left:8px; padding-top:5px;">DXL Scanner</h3>\
            				<div class="menus">\
            					<span style="font-size:14px; font-weight:bold; padding-left:8px;">Menus</span>\
                                \
            					<div class="projects">\
            						<a href="projects_tree.html" style="margin-top: 6px; padding-top:3px; padding-bottom:3px; padding-left:25px;">Projects</a>\
            					</div>\
            					<div class="addins">\
            						<a href="addins_tree.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Addins</a>\
            					</div>\
            					<div class="extra">\
            						<a href="extra_tree.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Extras</a>\
            					</div>\
            				</div>\
            				<br>\
            					\
            				<div class="list-files">\
            					<span style="font-size:14px; font-weight:bold;">\
            						<a href="list.html" style="padding-left:8px; padding-top:3px; padding-bottom:3px;">Files and includes</a>\
            					</span>\
            				</div>\
            				<br>\
                            <div class="list-dependencies">\
            					<span style="font-size:14px; font-weight:bold; padding-left:8px;">Dependencies</span>\
                                \
            					<div class="projects">\
            						<a href="report_dependencies_projects.html" style="margin-top: 6px; padding-top:3px; padding-bottom:3px; padding-left:25px;">Projects</a>\
            					</div>\
            					<div class="addins">\
            						<a href="report_dependencies_addins.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Addins</a>\
            					</div>\
            					<div class="extra">\
            						<a href="report_dependencies_extra.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Extras</a>\
            					</div>\
            				</div>\
                            <br>\
                            <div class="list-functions">\
            					<span style="font-size:14px; font-weight:bold;">\
            						<a href="list_functions.html" style="padding-left:8px; padding-top:3px; padding-bottom:3px;">Defined functions</a>\
            					</span>\
            				</div>\
            				<br>\
            					\
            				<div class="issues">\
            					<span style="font-size:14px; font-weight:bold; padding-left:8px;">Issues</span>\
            					<div class="report">\
            						<a href="report.html" style="margin-top: 6px; padding-top:3px; padding-bottom:3px; padding-left:25px;">Complete report</a>\
            					</div>\
            				</div>\
            				<br>\
            					\
            				<div class="categories">\
            					<span style="font-size:14px; font-weight:bold; padding-left:8px;">Issues categories</span>\
            					<div>\
            						<a href="report_include.html" style="margin-top: 6px; padding-top:3px; padding-bottom:3px; padding-left:25px;">Includes</a>\
            					</div>\
            					<div>\
            						<a href="report_pragma.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Pragma calls</a>\
            					</div>\
                                <div>\
                                    <a href="report_string%20initialization.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">String initializations</a>\
                                </div>\
            					<div>\
            						<a href="report_system.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">System calls</a>\
            					</div>\
                                <div>\
                                    <a href="report_cpd.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Code duplication</a>\
                                </div>\
            					<div>\
            						<a href="report_duplication.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Duplicated filenames</a>\
            					</div>\
                                <div>\
                                    <a href="report_include%20duplication.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Duplicated includes</a>\
            					</div>\
            					<div style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Function duplications</div>\
            					<div>\
            						<a href="report_function.html" style="padding-top:2px; padding-bottom:2px; padding-left:35px;">&bull; inside a file</a>\
            					</div>\
            					<div>\
            						<a href="report_function_global.html" style="padding-top:2px; padding-bottom:2px; padding-left:35px;">&bull; for different files</a>\
            					</div>\
                                <br>\
                                <div>\
                                    <a href="report_function_not_called.html" style="padding-top:3px; padding-bottom:3px; padding-left:25px;">Functions defined but not called</a>\
                                </div>\
            				</div>\
            				<br>\
            				\
            				<div class="log">\
            					<span style="font-size:14px; font-weight:bold;">\
            						<a href="'+ log_file_name +'" style="padding-left:8px; padding-top:3px; padding-bottom:3px;">Last log file</a>\
            					</span>\
            				</div>\
            				<br>\
            			</div>\
            			\
            			<div id="col" style="margin:0 auto;">\
            				<div style="float:left; border:1px solid #DCDEDC; background:#FFF; margin:10px; margin-right:1px; padding:5px; font-size:17px; width:35%;">\
                                <div>\
                                    <div style="float:left; margin:10px; padding-right:20px; padding-bottom:5px;">\
                						Lines of code\
                						<a href="list.html"><b>'+ str(count_lines) +'</b></a>\
                						Functions\
                						<a href="list_functions.html"><b>'+ str(count_functions) +'</b></a>\
                					</div>\
            					   \
                					<div style="float:left; margin:10px; padding-bottom:5px;">\
                						DXL files\
                						<a href="list.html"><b>'+ str(count_files) +'</b></a>\
                						Includes\
                						<a href="list.html"><b>'+ str(count_includes) +'</b></a>\
                						Directories\
                						<a><b>'+ str(count_dirs) +'</b></a>\
                					</div>\
            				    </div>\
            				    \
                				<div style="left: 175px; border:1px solid #DCDEDC; background:#FFF; margin-top:170px; margin-right:1px; margin-left:10px; padding:5px; font-size:17px; width:35%; position:absolute;">\
                					<div style="float:left; margin:10px; padding-right:20px; padding-bottom:5px;">\
                						Issues\
                						<a href="report.html"><b>'+ str(count_issues) +'</b></a>\
                					</div>\
                                    <!--<div style="float:left; margin:10px; padding-bottom:5px;">\
                                        Duplications\
                						<a href="report_cpd.html"><b>dup%</b></a>\
                                    </div>-->\
                				</div>\
            				</div>\
                            \
                            <div style="float:left; border:1px solid #DCDEDC; background:#FFF; margin:10px; padding:5px; font-size:17px; width:36%;">\
            					<div style="margin:10px;">\
            						Last scan <br>\
            						<span style="font-size:20px;"><b>'+ last_scan_date +'</b></span>\
            					</div>\
            					<div style="margin:10px;">\
                                    Last scan by user <br>\
            						<span style="font-size:20px;"><b>'+ user_tgi +'</b></span>\
            					</div>\
            					<div style="margin:10px;">\
            						Scanned directories <br>\
            						<span style="font-size:20px;"><b>'+ str(scanned_dirs_list).strip("[]").replace("'"," ") +'</b></span>\
            					</div>\
            				</div>\
            				\
            				<div style="left: 175px; border:1px solid #DCDEDC; background:#FFF; margin-top:280px; margin-right:1px; margin-left:10px; padding:5px; font-size:17px; width:74%; position:absolute;">\
					           <div style="margin:0px; padding-right:5px; padding-bottom:5px;">\
						          <iframe src="embedded_list.html" style="width: 100%; height: 700px" scrolling="yes" marginwidth="0" marginheight="0" frameborder="1" vspace="0" hspace="0"></iframe>\
					           </div>\
				            </div>\
            				\
            			</div>\
            		</div>\
            \
            	</body>\
            </font></html>'

        return self.homepage
