import ply.lex
import re

class Lexer:
    def __init__(self):
        self.__last_newline_lexpos = 0

    class Token:
        def __init__(self,value=None,type=None,line=0,column=0):
            self.value = value
            self.type = type
            self.line = line
            self.column = column

    #-----------------------------------------------------------------------------------------
    # Tokens definitions
    #-----------------------------------------------------------------------------------------
    reserved_base = (
        'AND', 'BOOL', 'BREAK', 'BY', 'CASE', 'CHAR', 'CONST', 'CONTINUE',
        'DEFAULT', 'DO', 'ELSE', 'ELSEIF', 'ENUM', 'FOR', 'IF', 'IN', 'INT', 'OR',
        'REAL', 'RETURN', 'SIZEOF', 'STATIC', 'STRUCT', 'STRING',
        'SWITCH', 'THEN', 'UNION', 'VOID', 'WHILE'
    )

    reserved_other = (
        'MODULE', 'OBJECT', 'SKIP', 'BUFFER', 'TEMPLATE', 'MODULE_VERSION',
        'DATE', 'LINK', 'LINK_REF', 'STREAM', 'REGEXP', 'ATTR_DEF', 'DB', 'DBE'
    )

    tokens = reserved_base + reserved_other + (
        # Literals (integer constant, float constant, character constant, string constant) and IDs
        'ICONST', 'FCONST', 'CCONST', 'SCONST', 'ID',

        # Operators (+,-,*,/,%,~,^,<<,>>,||,&&,!,<>,<,<=,>,>=,==,!=)
        'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD', 'NOT', 'XOR',
        'LSHIFT', 'RSHIFT', 'LOR', 'LAND', 'LNOT', 'TMPC','LT', 'LE', 'GT',
        'GE', 'EQ', 'NE',

        # Assignment (=, *=, /=, %=, +=, -=, <<=, >>=, &=, ^=, |=, <-, .., ::)
        'EQUALS', 'TIMESEQUAL', 'DIVEQUAL', 'MODEQUAL', 'PLUSEQUAL', 'MINUSEQUAL',
        'LSHIFTEQUAL','RSHIFTEQUAL', 'ANDEQUAL', 'XOREQUAL', 'OREQUAL', 'INLINK',
        'OVRLOAD','DEF',

        # Delimeters ( ) [ ] { } , . ; : ' "
        'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET', 'LBRACE', 'RBRACE',
        'COMMA', 'PERIOD', 'SEMI', 'COLON', 'SQUOTE', 'DQUOTE',

        # Comments
        'C_COMMENT', 'CPP_COMMENT',

        # Includes
        'INCLUDE', 'INCLUDE_PATH',

        # Functions
        'SYS_CALL', 'PRAGMA', 'FUNCTION',

        # Variable initializations
        'STRING_INIT', 'ERR_INIT_VAR', 'VAR_SINGLE_LINE',

        # Misc.
        'ARRAY_DEF', 'BR'
    )

    #------------------------------------------------------------------------------------------
    # Reserved identifiers
    #------------------------------------------------------------------------------------------
    reserved_map = dict()
    # lower all base types
    for base_type in reserved_base:
        reserved_map[base_type.lower()] = base_type
    for other_type in reserved_other:
        # leave these types in capital
        if other_type in ["DB","DBE"]:
            reserved_map[other_type] = other_type
        else:
            # TOK_TOK -> TokTok
            if "_" in other_type:
                type_list = other_type.split("_")
                reserved_map[type_list[0].capitalize()+type_list[1].capitalize()] = other_type
            # Capitalize others
            else:
                reserved_map[other_type.capitalize()] = other_type

    #-------------------------------------------------------------------------------------
    # Regex for simple tokens
    #-------------------------------------------------------------------------------------

    # Operators
    t_PLUS             = r'\+'
    t_MINUS            = r'-'
    t_TIMES            = r'\*'
    t_DIVIDE           = r'/'
    t_MOD              = r'%'
    t_OR               = r'\|'
    t_AND              = r'&'
    t_NOT              = r'~'
    t_XOR              = r'\^'
    t_LSHIFT           = r'<<'
    t_RSHIFT           = r'>>'
    t_LOR              = r'\|\|'
    t_LAND             = r'&&'
    t_LNOT             = r'!'
    t_TMPC             = r'<>'
    t_LT               = r'<'
    t_GT               = r'>'
    t_LE               = r'<='
    t_GE               = r'>='
    t_EQ               = r'=='
    t_NE               = r'!='

    # Assignment operators
    t_EQUALS           = r'='
    t_TIMESEQUAL       = r'\*='
    t_DIVEQUAL         = r'/='
    t_MODEQUAL         = r'%='
    t_PLUSEQUAL        = r'\+='
    t_MINUSEQUAL       = r'-='
    t_LSHIFTEQUAL      = r'<<='
    t_RSHIFTEQUAL      = r'>>='
    t_ANDEQUAL         = r'&='
    t_OREQUAL          = r'\|='
    t_XOREQUAL         = r'\^='
    t_INLINK           = r'<-'
    t_OVRLOAD          = r'\.\.'
    t_DEF              = r'::'

    # Delimiters
    t_LPAREN           = r'\('
    t_RPAREN           = r'\)'
    t_LBRACKET         = r'\['
    t_RBRACKET         = r'\]'
    t_LBRACE           = r'\{'
    t_RBRACE           = r'\}'
    t_COMMA            = r','
    t_PERIOD           = r'\.'
    t_SEMI             = r';'
    t_COLON            = r':'

    # Integer literal
    t_ICONST = r'\d+([uU][lL]|[lL][uU]|[uU]|[lL])?'

    # Floating literal
    t_FCONST = r'((\d*)(\.\d+)([eE](\+|-)?(\d+))? | (\d+)[eE](\+|-)?(\d+) | (\d+\.)([eE](\+|-)?(\d+))?)([lL]|[fF])?'

    # Character constant
    t_CCONST = r'(L)?\'([^\\\n]|(\\.))*?\''

    # String literal
    t_SCONST = r'\"([^\\\n]|(\\.))*?\"'

    # includes
    t_INCLUDE = r'\#include'
    t_INCLUDE_PATH = r'<[^0-9][^>;)\+]+>'

    t_BR = r'<br>'

    #--------------------------------------------------------------------------------------
    # Regex functions for complex tokens - Priority: before nestedcode
    #--------------------------------------------------------------------------------------

    """def t_ERR_INIT_VAR(self,t):
        r'(?!(string|int|bool)\s+\w+[ \t\f\v]*(,\s*\w+|)+=)(string|int|bool)\s+\w+[ \t\f\v]*(,\s*\w+|)+'
        return t"""

    """def t_VAR_SINGLE_LINE(self,t):
        r'((string|int|bool|char)\s+\w+[ \t\f\v]*(,\s*\w+)+\s*=.*)|(.*;.*)'
        return t"""

    def t_STRING_INIT(self,t):
        r'string(\s+)\w+(\s+|)=(\s+|)'
        return t

    def t_ARRAY_DEF(self,t):
        r'(.*)(\s*|)\[\](\s*|)=(\s*|)\{.*\}'
        return t

    #--------------------------------------------------------------------------------------
    # Other regex functions - No priority, after nestedcode
    #--------------------------------------------------------------------------------------

    def t_SYS_CALL(self,t):
        r'^system(\s|)\(.*\)|^system(\s|)\".*\"|^system\s(.*)|win32SystemWait_ .*|addMenu|allowNetworkMonitor'
        return t

    def t_PRAGMA(self,t):
        r'pragma\s(xflags|runLim|stack|encoding)(,(\s|)[\d\w\"-]*|)'
        return t

    def t_FUNCTION(self,t):
        r'(?!(if|else|for|while)\b)\b\w+\s?\((.*|)\)(?!\s*?\{)'
        return t

    def t_CPP_COMMENT(self,t):
        r'//[^\n\\]*(\\\s*[^\n\\]*)*'
        t.lexer.lineno += t.value.count("\n")
        return t

    def t_C_COMMENT(self,t):
        r'/\*(.|\n)*?\*/'
        t.lexer.lineno += t.value.count("\n")
        return t

    def t_ID(self,t):
        r'[A-Za-z_][\w_]*'
        if self.reserved_map.get(t.value) != None:
            t.type = self.reserved_map.get(t.value)
        return t

    def t_newline(self,t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")
        self.__last_newline_lexpos = t.lexer.lexpos

    def t_ANY_error(self,t):
        ##print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    t_ANY_ignore = ' \t'

    def build(self,**kwargs):
        self.lexer = lex.lex(module=self, **kwargs)


    def get_tokens(self,data):
        """
            Gets tokens of interest to analyze them in dxl_scan.py
        """

        self.lexer.input(data)

        self.is_exec_by_doors = False
        self.include_dict = dict()
        self.string_init_dict = dict()
        self.string_init_loop_dict = dict()
        self.pragma_dict = dict()
        self.sys_call_dict = dict()
        self.var_single_line_dict = dict()

        previous_token_is_include = False
        previous_token_is_string_init = False
        previous_token_is_cpp_comment = False

        count_tok = 0
        is_first_token = False

        # test get called function
        keywords = ["BOOL","CHAR","INT","STRING","REAL","VOID","OBJECT","MODULE"]
        self.func_called = []
        previous_token_is_keyword = False

        has_loop = False
        in_loop = False
        count_brace = 0

        while True:
            tok = self.lexer.token()
            if not tok:
                break

            # Include tokens
            if previous_token_is_include:
                if tok.type in ["INCLUDE_PATH","SCONST"]:
                    v = tok.value[1:-1]
                    l = tok.lineno
                    self.include_dict[v] = l

            # String initialization tokens
            if previous_token_is_string_init:
                v = tok.value
                l = tok.lineno
                self.string_init_dict[v] = l

            # String initialization in loop
            if tok.type in ["FOR","WHILE"]:
                has_loop = True
            if tok.type == "LBRACE" and has_loop:
                in_loop = True
                count_brace += 1
            elif tok.type == "RBRACE" and has_loop:
                count_brace -= 1
                if count_brace == 0:
                    in_loop = False
                    has_loop = False
            if in_loop:
                if tok.type == "STRING_INIT":
                    v = tok.value
                    l = tok.lineno
                    self.string_init_loop_dict[v] = l

            """# More than one instruction on a line
            if tok.type == "VAR_SINGLE_LINE":
                v = tok.value
                l = tok.lineno
                self.var_single_line_dict[v] = l"""

            # Pragma tokens
            if tok.type == "PRAGMA":
                v = tok.value
                l = tok.lineno
                self.pragma_dict[v] = l

            # System calls tokens
            if tok.type == "SYS_CALL":
                v = tok.value
                l = tok.lineno
                self.sys_call_dict[v] = l
            if tok.type == "FUNCTION":
                if tok.value[:6] == "system":
                    v = tok.value
                    l = tok.lineno
                    self.sys_call_dict[v] = l

            # File executable by DOORS
            if tok.type == "CPP_COMMENT" and count_tok == 1:
                is_first_token = True
            if previous_token_is_cpp_comment and is_first_token and tok.type == "C_COMMENT":
                self.is_exec_by_doors = True

            # Called functions
            if tok.type == "FUNCTION" and not previous_token_is_keyword:
                tok.value = tok.value.split("(")[0]
                self.func_called.append(tok.value)

            previous_token_is_include = tok.type == "INCLUDE"
            previous_token_is_string_init = tok.type == "STRING_INIT"
            previous_token_is_cpp_comment = tok.type == "CPP_COMMENT"
            previous_token_is_keyword = tok.type in keywords


    def get_func_declarations(self,data):
        """
            Returns a dictionnary of declared functions names as key
            and a list of lines where they are declared as value
        """

        self.lexer.input(data)
        func_name_dict = dict()
        previous_token_is_keyword = False
        keywords = ["BOOL","CHAR","INT","STRING","REAL","VOID","OBJECT","MODULE","SKIP"]

        func_re = re.compile(r'(bool|char|int|string|real|void|Object|Module)[ \t]{1,}(?P<func_name>[\w]*)([ \t]|)\(.*\)(\s|){0,}\{([^\}]*|)\}')
        func_names = [match.group('func_name') for match in func_re.finditer(data)]

        while True:
            func_line_list = []

            tok = self.lexer.token()
            if not tok:
                break

            if tok.type == "FUNCTION" and previous_token_is_keyword:
                tok.value = tok.value.split("(")[0]

            if tok.value in func_names:
                if tok.value in func_name_dict:
                    func_name_dict[tok.value].append(tok.lineno)
                else:
                    func_line_list.append(tok.lineno)
                    func_name_dict[tok.value] = func_line_list

            previous_token_is_keyword = tok.type in keywords

        return func_name_dict


    def init(self,data):
        """
            Main Lexer function
            Returns a dictionnary with line number as key
            and a Token objects list as value
        """

        self.lexer.input(data)
        self.tok_dict = dict()
        self.tok_list = []

        while True:
            tok = self.lexer.token()

            if not tok:
                break

            if tok.type == "CPP_COMMENT":
                if tok.value.startswith("//#include") or tok.value.startswith("// #include"):
                    tok.value = tok.value.replace("<","&lt").replace(">","&gt")
            elif tok.type == "C_COMMENT":
                tok.value = tok.value.replace("\n","<br>\n").replace("\t","&nbsp;"*8).replace(" ","&nbsp;")
            elif tok.type == "NESTEDCODE":
                tok.value = tok.value.replace("\n","<br>\n")#.replace("\t","&nbsp;"*8).replace(" ","&nbsp;"*2)

            # some SYS_CALL tokens are mistaken for FUNCTION ones
            if tok.type == "FUNCTION":
                if tok.value[:6] == "system":
                    tok.type = "SYS_CALL"

            column = tok.lexpos - self.__last_newline_lexpos
            if not tok.lineno in self.tok_dict:
                self.tok_dict[tok.lineno] = []

            t = self.Token(tok.value,tok.type,tok.lineno,column)
            self.tok_dict[tok.lineno].append(t)
