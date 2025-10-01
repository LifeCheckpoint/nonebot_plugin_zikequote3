class CommandParseResult:
    command: str = ""
    flags: dict[str, str | None] = {}
    default_arg: str | None = None

class CommandParser:
    def __init__(self, known_commands, known_flags):
        """
        初始化解析器

        :param known_commands: 已知命令头的列表，如 ['查语录', '加语录']
        :param known_flags: 已知标志的字典。例如 '-t': {'has_arg': ..., 'long': '--test' | None}
        """
        self.known_commands = known_commands
        self.known_flags = known_flags
        # 构建一个按长度降序排列的标志名列表，用于最长匹配
        self._all_flag_names = sorted(
            [f for f in known_flags.keys()],
            key=len,
            reverse=True
        )

    def parse(self, input_string):
        """
        解析输入字符串
        :param input_string: 原始输入，包含命令头
        :return: 解析结果字典，格式为
        """
        # 初始化状态和结果
        self.input = input_string
        self.index = 0
        self.len_input = len(input_string)
        
        self.result = CommandParseResult()
        self.state = '寻找命令头'

        # 开始状态机循环
        while self.index < self.len_input:
            if self.state == '寻找命令头':
                self._parse_command()
            elif self.state == '寻找标志或默认参数':
                self._parse_flags_or_default_arg()

        return self.result

    def _parse_command(self):
        """状态：寻找命令头"""
        # 跳过开头的'/'
        if self.input[self.index] == '/':
            self.index += 1

        # 尝试匹配所有已知命令头
        for cmd in self.known_commands:
            if self.input.startswith(cmd, self.index):
                self.result.command = cmd
                self.index += len(cmd)
                self.state = '寻找标志或默认参数'
                return

        # 如果没有匹配到任何已知命令头，报错或处理
        raise ValueError(f"在位置 {self.index} 未找到已知命令头")

    def _parse_flags_or_default_arg(self):
        """状态：寻找标志或默认参数"""
        # 如果当前位置以 '-' 开头，尝试解析标志
        if self.input[self.index] == '-':
            # 尝试所有可能的标志名（按长度降序）
            for flag_name in self._all_flag_names:
                if self.input.startswith(flag_name, self.index):
                    self._handle_flag(flag_name)
                    return
            
            # 如果没有匹配到已知标志，将其视为默认参数的一部分
            self._start_default_arg()
        else:
            # 不是以 '-' 开头，直接开始收集默认参数
            self._start_default_arg()

    def _handle_flag(self, flag_name):
        """处理匹配到的标志"""
        flag_info = self.known_flags[flag_name]
        
        # 移动到标志名之后
        self.index += len(flag_name)
        
        if flag_info['has_arg']:
            # 这个标志需要参数，使用贪心匹配策略
            arg = self._greedy_collect_flag_arg()
            self.result.flags[flag_name] = arg
        else:
            # 无参数标志
            self.result.flags[flag_name] = None

    def _greedy_collect_flag_arg(self):
        """
        贪心收集标志参数
        核心逻辑：只有当后面确实出现了一个已知的标志时，才结束当前参数的收集
        """
        start_pos = self.index
        arg_end = self.len_input  # 默认到字符串结尾
        
        # 查找下一个已知标志的开始位置
        for next_flag in self._all_flag_names:
            next_pos = self.input.find(next_flag, self.index)
            if next_pos != -1 and next_pos < arg_end:
                # 只有当这个位置确实是一个标志的开始时才更新结束位置
                if next_pos >= self.index:
                    arg_end = next_pos
        
        # 提取参数
        arg = self.input[self.index:arg_end]
        self.index = arg_end
        return arg

    def _start_default_arg(self):
        """收集默认参数"""
        self.result.default_arg = self.input[self.index:]
        self.index = self.len_input  # 跳到结尾，结束解析

if __name__ == "__main__":
    known_commands = ['查语录', '加语录']
    known_flags = {
        '-t': {'has_arg': True, 'long': '--test'},
        '--test': {'has_arg': True, 'short': '-t'},
        '-g': {'has_arg': False, 'long': '--GLOBAL'},
        '--GLOBAL': {'has_arg': False, 'short': '-g'},
        '-a': {'has_arg': False, 'long': None}
    }

    parser = CommandParser(known_commands, known_flags)
    
    # 测试用例 - 重点测试贪心匹配
    test_cases = [
        '/查语录-t你知道吗a-b等于-1！-g-a你好我好大家好\n\n"test"',
        '/查语录-t-g-a',
        '/查语录-t-hi-g-a',
        '/查语录-t--help-g-a',
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"输入: {test_input}")
        
        result = parser.parse(test_input)
        print("解析结果:")
        print(f"命令头: {result.command}")
        for flag, arg in result.flags.items():
            if arg is None:
                print(f"{flag}")
            else:
                print(f"{flag} | {arg}")
        if result.default_arg:
            print(f"默认参数 | {result.default_arg}")
