import pytest
from nonebot_plugin_zikequote3.utils.command_parser import CommandParser, CommandParseResult


class TestCommandParser:
    """测试命令解析器"""

    @pytest.fixture
    def known_commands(self):
        """已知命令列表"""
        return ['查语录', '加语录', '删语录', '改语录']

    @pytest.fixture
    def known_flags(self):
        """已知标志配置"""
        return {
            '-t': {'has_arg': True, 'long': '--test'},
            '--test': {'has_arg': True, 'short': '-t'},
            '-g': {'has_arg': False, 'long': '--GLOBAL'},
            '--GLOBAL': {'has_arg': False, 'short': '-g'},
            '-a': {'has_arg': False, 'long': None},
            '-n': {'has_arg': True, 'long': '--number'},
            '--number': {'has_arg': True, 'short': '-n'}
        }

    @pytest.fixture
    def parser(self, known_commands, known_flags):
        """命令解析器实例"""
        return CommandParser(known_commands, known_flags)

    def test_parse_basic_command(self, parser):
        """测试基本命令解析"""
        result = parser.parse('查语录')
        assert result.command == '查语录'
        assert result.flags == {}
        assert result.default_arg is None

    def test_parse_command_with_slash(self, parser):
        """测试带斜杠的命令解析"""
        result = parser.parse('/查语录')
        assert result.command == '查语录'
        assert result.flags == {}
        assert result.default_arg is None

    def test_parse_command_with_flag_no_arg(self, parser):
        """测试带无参数标志的命令解析"""
        result = parser.parse('查语录 -g')
        assert result.command == '查语录'
        assert result.flags == {'-g': None}
        assert result.default_arg is None

    def test_parse_command_with_flag_with_arg(self, parser):
        """测试带参数标志的命令解析"""
        result = parser.parse('查语录 -t 测试参数')
        assert result.command == '查语录'
        assert result.flags == {'-t': '测试参数'}
        assert result.default_arg is None

    def test_parse_command_with_multiple_flags(self, parser):
        """测试多个标志的命令解析"""
        result = parser.parse('查语录 -t 参数1 -g -a')
        assert result.command == '查语录'
        assert result.flags == {'-t': '参数1', '-g': None, '-a': None}
        assert result.default_arg is None

    def test_parse_command_with_long_flags(self, parser):
        """测试长标志的命令解析"""
        result = parser.parse('查语录 --test 长参数 --GLOBAL')
        assert result.command == '查语录'
        assert result.flags == {'--test': '长参数', '--GLOBAL': None}
        assert result.default_arg is None

    def test_parse_command_with_default_arg(self, parser):
        """测试带默认参数的解析"""
        result = parser.parse('查语录 默认参数内容')
        assert result.command == '查语录'
        assert result.flags == {}
        assert result.default_arg == '默认参数内容'

    def test_parse_command_with_flags_and_default_arg(self, parser):
        """测试标志和默认参数同时存在的情况"""
        result = parser.parse('查语录 -t 标志参数 默认参数内容')
        assert result.command == '查语录'
        assert result.flags == {'-t': '标志参数'}
        assert result.default_arg == '默认参数内容'

    def test_parse_command_greedy_flag_arg(self, parser):
        """测试贪心标志参数匹配"""
        # 测试用例来自原始代码的示例
        result = parser.parse('/查语录-t你知道吗a-b等于-1！-g-a你好我好大家好\n\n"test"')
        assert result.command == '查语录'
        assert result.flags == {
            '-t': '你知道吗a-b等于-1！',
            '-g': None,
            '-a': None
        }
        assert result.default_arg is None

    def test_parse_command_complex_greedy_matching(self, parser):
        """测试复杂贪心匹配场景"""
        test_cases = [
            ('查语录-t-hi-g-a', {'-t': '-hi', '-g': None, '-a': None}),
            ('查语录-t--help-g-a', {'-t': '--help', '-g': None, '-a': None}),
            ('查语录-n 123 -g', {'-n': '123', '-g': None}),
        ]

        for input_str, expected_flags in test_cases:
            result = parser.parse(input_str)
            assert result.command == '查语录'
            assert result.flags == expected_flags
            assert result.default_arg is None

    def test_parse_command_with_flag_at_end(self, parser):
        """测试标志在末尾的情况"""
        result = parser.parse('查语录 -t 参数内容 -g')
        assert result.command == '查语录'
        assert result.flags == {'-t': '参数内容', '-g': None}
        assert result.default_arg is None

    def test_parse_command_with_only_default_arg(self, parser):
        """测试只有默认参数的情况"""
        result = parser.parse('查语录 这是一段很长的默认参数内容，包含各种字符!@#$%^&*()')
        assert result.command == '查语录'
        assert result.flags == {}
        assert result.default_arg == '这是一段很长的默认参数内容，包含各种字符!@#$%^&*()'

    def test_parse_command_with_whitespace(self, parser):
        """测试带空格的命令解析"""
        result = parser.parse('  查语录  -t   参数  -g  ')
        assert result.command == '查语录'
        assert result.flags == {'-t': '参数', '-g': None}
        assert result.default_arg is None

    def test_parse_unknown_command(self, parser):
        """测试未知命令的异常处理"""
        with pytest.raises(ValueError, match="未找到已知命令头"):
            parser.parse('未知命令 -t 参数')

    def test_parse_empty_string(self, parser):
        """测试空字符串输入"""
        with pytest.raises(ValueError, match="未找到已知命令头"):
            parser.parse('')

    def test_parse_only_slash(self, parser):
        """测试只有斜杠的情况"""
        with pytest.raises(ValueError, match="未找到已知命令头"):
            parser.parse('/')

    def test_parse_command_parse_result_structure(self, parser):
        """测试解析结果结构"""
        result = parser.parse('加语录 -t 测试 -g')
        assert isinstance(result, CommandParseResult)
        assert hasattr(result, 'command')
        assert hasattr(result, 'flags')
        assert hasattr(result, 'default_arg')
        assert isinstance(result.flags, dict)

    def test_parse_different_commands(self, parser):
        """测试不同的命令头"""
        commands = ['查语录', '加语录', '删语录', '改语录']
        for cmd in commands:
            result = parser.parse(cmd)
            assert result.command == cmd
            assert result.flags == {}
            assert result.default_arg is None

    def test_parse_command_with_mixed_long_short_flags(self, parser):
        """测试混合长短标志"""
        result = parser.parse('查语录 -t 短参数 --test 长参数 -g --GLOBAL')
        assert result.command == '查语录'
        # 注意：由于贪心匹配，第一个-t会匹配到整个参数
        assert result.flags == {'-t': '短参数 --test 长参数', '-g': None, '--GLOBAL': None}

    def test_parse_command_with_special_characters(self, parser):
        """测试特殊字符处理"""
        result = parser.parse('查语录 -t "带引号的参数" -g')
        assert result.command == '查语录'
        assert result.flags == {'-t': '"带引号的参数"', '-g': None}
        assert result.default_arg is None

    def test_parse_command_with_newlines(self, parser):
        """测试换行符处理"""
        result = parser.parse('查语录 -t 参数1\n参数2 -g')
        assert result.command == '查语录'
        assert result.flags == {'-t': '参数1\n参数2', '-g': None}
        assert result.default_arg is None


class TestCommandParserEdgeCases:
    """测试边界情况"""

    def test_parser_with_empty_known_commands(self):
        """测试空命令列表"""
        parser = CommandParser([], {})
        with pytest.raises(ValueError):
            parser.parse('任何命令')

    def test_parser_with_empty_known_flags(self):
        """测试空标志配置"""
        parser = CommandParser(['查语录'], {})
        result = parser.parse('查语录 -unknown 参数')
        assert result.command == '查语录'
        assert result.flags == {}
        assert result.default_arg == '-unknown 参数'

    def test_parser_flag_with_only_long_form(self):
        """测试只有长形式的标志"""
        known_flags = {
            '--only-long': {'has_arg': True, 'short': None}
        }
        parser = CommandParser(['查语录'], known_flags)
        result = parser.parse('查语录 --only-long 参数值')
        assert result.command == '查语录'
        assert result.flags == {'--only-long': '参数值'}
        assert result.default_arg is None

    def test_parser_flag_with_only_short_form(self):
        """测试只有短形式的标志"""
        known_flags = {
            '-o': {'has_arg': False, 'long': None}
        }
        parser = CommandParser(['查语录'], known_flags)
        result = parser.parse('查语录 -o')
        assert result.command == '查语录'
        assert result.flags == {'-o': None}
        assert result.default_arg is None