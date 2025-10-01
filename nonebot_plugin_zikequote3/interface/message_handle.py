from .. import __plugin_meta__
from ..imports import *
from ..imports import cfg
from ..utils.llm_solo import llm_solo
from ..utils.states import HistoryQuoteState

def validate_msg(event: GroupME) -> bool:
    """验证事件中的消息是否符合一般收录条件"""
    message = event.get_plaintext().strip()
    if not message or message == "" or len(message) > cfg.get("collecting")["msg_max_length"]:
        return False
    return True

def get_typed_message_list(group_id: int, filter: Callable[[ChatMessageV3], bool] = lambda msg: True) -> List[ChatMessageV3]:
    """获取指定群组的消息列表"""
    chat = ChatHistoryManager(__plugin_meta__.name, "history", get_msg_file_name(group_id))
    with chat:
        messages = chat.get_typed_messages()
        return [msg for msg in messages if filter(msg)]

async def get_group_member_cardname(group_id: int, user_id: int, bot: Bot) -> str:
    """获取群组成员的群名片"""
    name = (await bot.get_group_member_info(group_id=group_id, user_id=user_id, no_cache=False)).get("card")
    return name if name else ""

def add_mapping(group_id: int, message_id: int, quote_id: int):
    """添加消息 ID 和语录 ID 的映射关系"""
    state = HistoryQuoteState(get_mapping_file(group_id))
    state.add_mapping(message_id, quote_id)

def get_mapping(group_id: int, message_id: int) -> Optional[int]:
    """获取消息 ID 和语录 ID 的映射关系"""
    state = HistoryQuoteState(get_mapping_file(group_id))
    return state.get_mapping(message_id)

async def pick_received_msg(event: GroupME, bot: Bot) -> Optional[bool]:
    """
    监听群组消息，处理可能的语录收集

    `return`: None: 已收集但未处理，False: 处理失败，True: 处理成功
    """    
    if not validate_msg(event):
        return

    msg_id = event.message_id
    group_id = event.group_id
    group_name = event.get_session_id()
    user_id = event.user_id
    user_group_nickname = await get_group_member_cardname(group_id, user_id, bot)
    user_name = event.sender.nickname or ""
    time_stamp = event.time

    msg_file_name = get_msg_file_name(group_id)

    # 更新群组消息记录文件，完成后保存
    chat = ChatHistoryManager(__plugin_meta__.name, "history", msg_file_name)
    with chat:
        chat.add_message(ChatMessageV3(
            message_id=msg_id,
            source_group_id=group_id,
            source_group_name=group_name,
            source_user_id=user_id,
            source_user_name=user_name,
            source_user_nickname=user_group_nickname,
            time_stamp=time_stamp,
            message=event.get_plaintext().strip()
        ))

    # 到达条数，触发更新并尝试清空
    if len(chat.get_messages()) >= cfg.pickup_interval:
        return await read_msg_and_pickup(group_id)

async def read_msg_and_pickup(group_id: int) -> bool:
    """读取消息并进行语录筛选提取"""
    chat = ChatHistoryManager(__plugin_meta__.name, "history", get_msg_file_name(group_id))
    chat.load_from_file()
    result = await LLM_quote_pickup(group_id, chat.get_typed_messages())

    if result:
        chat.clear_messages()
    else:
        chat.clip_messages(cfg.pickup_interval - 1)
    chat.save_to_file()
    
    return result

@serial_execution
async def LLM_quote_pickup(group_id: int, message_list: List[ChatMessageV3]) -> bool:
    """调用 LLM 进行语录筛选提取"""
    if len(message_list) == 0:
        print("[WARNING] 消息列表为空，可能需要检查相关配置是否正确")
        return False
    
    prompt_quote_pickup = (cfg.path.prompts / "quote_pickup.txt").read_text(encoding="utf-8")
    full_prompt = template(prompt_quote_pickup, {
        "message_history": "\n".join([f"({msg.message_id}) {msg.source_user_name}: {msg.message}" for msg in message_list])
    })

    try:
        result = await llm_solo(full_prompt)
        if result == None: raise ValueError("空值被返回")
    except Exception as e:
        print("LLM 筛选语录失败，错误信息：", e)
        return False
    
    # 解析语录
    try:
        result = json.loads(result)
        if not isinstance(result, dict) or "num_quotes" not in result or "quotes" not in result:
            raise ValueError("解析响应失败，请检查响应：", result)
    except Exception as e:
        print("解析 LLM 返回语录失败，错误信息：", e)
        return False
    
    print(f"收集到 {result['num_quotes']} 条语录")

    # 添加语录
    qm = QuoteManager(get_quote_file(group_id))
    qm.load_from_file()
    
    for quote in result["quotes"]:
        quote: dict

        # 获取 id
        target_msg_match_id = quote.get("id", -1)

        # 根据 id 查找消息
        message_data = next((msg for msg in message_list if str(msg.message_id) == str(target_msg_match_id)), None)
        if message_data is None:
            print(f"[Warning] 消息数据未找到: {target_msg_match_id}")
            continue

        # 检查重复
        if not cfg.enable_duplicate:
            duplicate_quote = [
                qu for qu in qm.get_typed_quotes()
                if qu.quote.strip() == quote["quote"].strip()
                and qu.author_id == message_data.source_user_id
            ]
            if len(duplicate_quote) > 0:
                print(f"[Warning] 语录重复，跳过: {quote["quote"]}")
                continue

        qm.add_quote(QuoteInfoV2(
            quote_id=target_msg_match_id,
            author_id=message_data.source_user_id,
            author_name=message_data.source_user_name,
            author_card=message_data.source_user_nickname,
            time_stamp=message_data.time_stamp,
            quote=quote["quote"],
        ))
        qm.add_comment(target_msg_match_id, QuoteV2Comment(
            content = quote["comment"],
            author_id = COMMENT_AUTHOR_AI,
            author_name = "AI",
            time_stamp=message_data.time_stamp
        ))

    qm.save_to_file()

    return True