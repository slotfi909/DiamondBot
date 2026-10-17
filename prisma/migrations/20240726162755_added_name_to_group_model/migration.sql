/*
  Warnings:

  - Added the required column `group_name` to the `Group` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Group" ADD COLUMN     "group_name" TEXT NOT NULL;
