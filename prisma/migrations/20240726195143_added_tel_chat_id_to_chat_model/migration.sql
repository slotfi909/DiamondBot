/*
  Warnings:

  - Added the required column `starter_tel_chat_id` to the `Chat` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Chat" ADD COLUMN     "receiver_tel_chat_id" INTEGER,
ADD COLUMN     "starter_tel_chat_id" INTEGER NOT NULL;
