/*
  Warnings:

  - You are about to drop the column `expired_at` on the `Chat` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "Chat" DROP COLUMN "expired_at",
ADD COLUMN     "exited_at" TIMESTAMP(3);
