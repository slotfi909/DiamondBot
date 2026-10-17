/*
  Warnings:

  - A unique constraint covering the columns `[national_code]` on the table `User` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "User_national_code_key" ON "User"("national_code");
