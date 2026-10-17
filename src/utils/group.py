from telegram import ChatMemberUpdated, ChatMember


def extract_status_change(chat_member_update: ChatMemberUpdated):
    return chat_member_update.new_chat_member.status == ChatMember.LEFT, chat_member_update.new_chat_member.status != ChatMember.LEFT
