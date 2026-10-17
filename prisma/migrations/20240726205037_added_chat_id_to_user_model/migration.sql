/*
  Warnings:

  - You are about to drop the column `receiver_tel_chat_id` on the `Chat` table. All the data in the column will be lost.
  - You are about to drop the column `starter_tel_chat_id` on the `Chat` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "Chat" DROP COLUMN "receiver_tel_chat_id",
DROP COLUMN "starter_tel_chat_id",
ADD COLUMN     "expired_at" TIMESTAMP(3);

-- AlterTable
ALTER TABLE "User" ADD COLUMN     "tel_chat_id" BIGINT NOT NULL DEFAULT 0,
ALTER COLUMN "tel_id" SET DATA TYPE BIGINT;
