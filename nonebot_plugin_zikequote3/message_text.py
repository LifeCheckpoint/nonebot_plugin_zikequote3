from typing import Optional, Dict, List, Tuple, Union

def msg_api_request_error(error: Optional[str] = None):
    """API 请求错误"""
    head = {
        "连接不上语录服务器了... 是不是网络坏掉了？": 1,
        "尝试连接服务器失败了... 网络连接正常吗？( T_T)": 1,
        "呜... 无法连接到语录服务器... 请稍后再试试吧 (＞﹏＜)": 1,
    }
    if error != None:
        return [head, "\n\n", "错误原因：", error]
    else:
        return [head]

def msg_send_quote(author: str, quote: str):
    """发送语录"""
    return {
        f"{author}曾经说过：{quote}": 1,
        f"{author}曰：{quote}": 1,
        f"{author}说：{quote}": 1,
        f"{author}：{quote}": 1,
        f"{quote}\n——{author}": 0.5,
    }

def msg_quote_not_found(key: Optional[str] = None):
    """语录未找到"""
    if key == None or key == "":
        return {
            "呜呜(っ﹏<。) 没有找到相关的语录呢...": 1,
            "查询失败...没找到相关的语录哦？": 1,
            "坏消息！没有找到符合条件的语录哦ヾ(≧へ≦)〃": 1,
            "抱歉，没找到符合条件的语录呢X﹏X": 1,
        }
    else:
        return {
            f"抱歉，没找到包含「{key}」的语录呢X﹏X": 1,
            f"呜呜(っ﹏<。) 没有找到包含「{key}」的语录呢...": 1,
            f"查询失败...没找到包含「{key}」的语录哦？": 1,
            f"坏消息！没有找到符合条件「{key}」的语录哦ヾ(≧へ≦)〃": 1,
        }
    
def msg_quote_on_update():
    """语录更新中"""
    return {
        "正在尝试更新语录...": 1,
        "正在更新语录o(*≧▽≦)ツ┏━┓": 1,
        "(∪.∪ )...zzz语录更新中！": 1,
    }

def msg_quote_update_success():
    """语录更新成功"""
    return {
        "语录更新成功啦！(≧∇≦)/": 1,
        "语录更新完成！(o゜▽゜)o☆": 1,
    }

def msg_quote_update_failed(error: Optional[str] = None):
    """语录更新失败"""
    return [{
        f"语录更新失败(っ °Д °;)っ...": 1,
        f"语录更新失败了呢o(TヘTo)...": 1,
    }, error if error else ""]

def msg_add_quote_reply_args_missing():
    """回复方式添加语录参数缺失"""
    return {
        "要回复一条文本消息哦⊙﹏⊙∥": 1,
        "要回复一条文本消息才能添加语录哦￣へ￣": 1,
        "这条回复里面什么都没说呢...": 1,
    }

def msg_comment_quote_reply_args_missing():
    """回复方式评论语录参数缺失"""
    return {
        "要回复一条语录哦⊙﹏⊙∥": 1,
        "要回复一条语录消息才能评论哦￣へ￣": 1,
        "这条回复里面什么都没说呢...": 1,
    }

def msg_add_quote_failed(error: Optional[str] = None):
    """添加语录失败"""
    reason = error or "我也不知道..."
    options = {
        f"Σ(っ °Д °;)っ 添加失败了... 原因：{reason}": 1,
        f"添加失败了呢... 服务器说：{reason} (╥﹏╥)": 1,
        f"糟糕！添加语录时遇到了问题：{reason} (⊙_⊙)": 1
    }
    return options

def msg_add_quote_success(author: Optional[str] = None):
    """添加语录成功"""
    options = {
        "语录添加成功啦！(≧∇≦)/": 1,
        "搞定！新的语录已经记下啦~ (ﾉ´ヮ´)ﾉ*:･ﾟ✧": 1,
        "添加成功！又多了一条可以回顾的记忆~ (*^▽^*)": 1
     } if not author else {
        f"添加成功！{author} 的语录已经记下啦~ (ﾉ´ヮ´)ﾉ*:･ﾟ✧": 1,
        f"搞定！{author} 的语录已经添加成功啦~ (≧∇≦)/": 1,
        f"好耶！{author} 的语录已经成功添加到我的记忆里了！(≧∇≦)/": 1
    }
    return options

def msg_remove_quote_reply_args_missing():
    """回复方式删除语录参数缺失"""
    return {
        "要回复一条语录哦(o゜▽゜)o☆": 1,
        "要回复一条语录消息才能删除语录哦~": 1,
    }

def quote_not_found():
    """删除语录未找到"""
    return {
        "没有找到对应的语录呢...可能太久远啦~": 1,
        "奇怪，没有找到对应的语录哦？(っ °Д °;)っ": 1,
        "没找到符合条件的语录呢~": 1,
    }

def msg_remove_quote_success(author: Optional[str] = None):
    """删除语录成功"""
    return {
        f"删除成功！{author} 的语录已经被删除啦~ (ﾉ´ヮ´)ﾉ*:･ﾟ✧": 1,
        f"搞定！{author} 的语录已经删除成功啦~ (≧∇≦)/": 1,
        f"好耶！{author} 的语录已经成功删除了！(≧∇≦)/": 1
    } if author != None else {
        "删除成功！语录已经被删除啦~ (ﾉ´ヮ´)ﾉ*:･ﾟ✧": 1,
        "搞定！语录已经删除成功啦~ (≧∇≦)/": 1,
        "好耶！语录已经成功删除了！(≧∇≦)/": 1
    }

def msg_remove_quote_failed(error: Optional[str] = None):
    """删除语录失败"""
    reason = error or "我也不知道..."
    options = {
        f"Σ(っ °Д °;)っ 删除失败了... 原因：{reason}": 1,
        f"删除失败了呢... 服务器说：{reason} (╥﹏╥)": 1,
        f"糟糕！删除语录时遇到了问题，问题是：{reason} (⊙_⊙)": 1
    }
    return options

def msg_quote_list_not_found(key: str):
    """语录列表未找到用户"""
    return {
        f"没有找到「{key}」这个群友╥﹏╥...已经输入全名了嘛？": 1,
        f"查询失败...没找到「{key}」这个群友哦？ヾ(≧へ≦)〃": 1,
    }

def msg_quote_list_ambiguous(key: str, num: int):
    """语录列表模糊匹配"""
    return {
        f"找到了「{key}」这个群友呢，但是有 {num} 个同名的群友哦~ 试试通过QQ号精确确认？(o゜▽゜)o☆": 1,
        f"有 {num} 个叫「{key}」的群友呢~ 试试用QQ号来精确确认？(●'◡'●)": 1,
    }

def msg_quote_search_empty():
    """语录搜索关键词为空"""
    return {
        "要输入一个关键词才能搜索哦(👉ﾟヮﾟ)👉": 1,
        "( *︾▽︾)~你还没有说要搜什么呢": 1,
    }

def msg_comment_quote_success():
    """评论语录成功"""
    return {
        "评论成功啦！(≧∇≦)/": 1,
        "搞定！评论已经记下啦~ (ﾉ´ヮ´)ﾉ*:･ﾟ✧": 1,
        "评论成功！又多了一条可以回顾的记忆~ (*^▽^*)": 1
    }

def msg_comment_quote_failed(error: Optional[str] = None):
    """评论语录失败"""
    reason = error or "我也不知道..."
    options = {
        f"Σ(っ °Д °;)っ 评论失败了... 原因：{reason}": 1,
        f"评论失败了呢... 服务器说：{reason} (╥﹏╥)": 1,
        f"糟糕！评论语录时遇到了问题，问题是...{reason} (⊙_⊙)": 1
    }
    return options

def msg_remove_quote_id_invalid():
    """删除语录 ID 无效"""
    return {
        "呜，要输入一个语录 ID 才能删除哦( ¯(∞)¯ )": 1,
        "要输入一个有效的语录 ID 才能删除哦￣へ￣": 1,
    }

def msg_quote_setting_showing_failed(error: Optional[str] = None):
    """语录设置生成失败"""
    reason = error or "我也不知道..."
    options = {
        f"语录设置...没有成功显示呢... 原因：{reason}": 1,
        f"服务器搞砸啦（＞人＜；）... 服务器说：{reason} (╥﹏╥)": 1,
        f"语录设置显示时出了点小故障...原因：{reason} (⊙_⊙)": 1
    }
    return options

def msg_quote_setting_update_failed(error: Optional[str] = None):
    """语录设置更新失败"""
    reason = error or "我也不知道..."
    options = {
        f"语录设置...没有成功更新呢... 原因：{reason}": 1,
    }
    return options

def msg_quote_setting_reload_failed(error: Optional[str] = None):
    """语录设置重载失败"""
    reason = error or "我也不知道..."
    options = {
        f"语录设置...没有成功重载呢... 服务器说：{reason}": 1,
    }
    return options