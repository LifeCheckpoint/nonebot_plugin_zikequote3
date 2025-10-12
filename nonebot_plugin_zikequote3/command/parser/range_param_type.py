import click

class RangeParamType(click.ParamType):
    name = "range"
    def convert(self, value, param, ctx):
        if not value or not isinstance(value, str):
            self.fail(f"无效的输入: {value!r}", param, ctx)
        parts = value.split("-", 1)
        
        try:
            # "start-end"
            if len(parts) == 2 and parts[1].strip() != "":
                start = int(parts[0])
                end = int(parts[1])
                
                if start < 0 or end < 0:
                    self.fail("页码不能为负数", param, ctx)
                
                if start > end:
                    self.fail("起始页码不能大于结束页码", param, ctx)
                
                # 如果 start 和 end 相等，直接返回单个整数
                if start == end:
                    return start
                
                return (start, end)
            # 单个数字 "page" 或 "page-"
            elif len(parts) == 1 or (len(parts) == 2 and parts[1].strip() == ""):
                page = int(parts[0])
                if page < 0:
                    self.fail("页码不能为负数", param, ctx)
                return page
            
            # 其他情况都无效
            else:
                self.fail(f"{value!r} 不是有效的页码或范围", param, ctx)
        except ValueError:
            self.fail(f"{value!r} 不是有效的页码或范围", param, ctx)
        except Exception as e:
            self.fail(f"处理 {value!r} 时发生错误: {e}", param, ctx)

PARAMTYPE_RANGE = RangeParamType()