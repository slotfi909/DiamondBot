/*
  Warnings:

  - You are about to drop the column `total_paid` on the `Order` table. All the data in the column will be lost.
  - You are about to drop the column `reffered_id` on the `Referral` table. All the data in the column will be lost.
  - A unique constraint covering the columns `[tel_chat_id]` on the table `User` will be added. If there are existing duplicate values, this will fail.
  - Made the column `payment_id` on table `Order` required. This step will fail if there are existing NULL values in that column.
  - Added the required column `referred_id` to the `Referral` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "Order" DROP CONSTRAINT "Order_payment_id_fkey";

-- DropForeignKey
ALTER TABLE "Referral" DROP CONSTRAINT "Referral_reffered_id_fkey";

-- AlterTable
ALTER TABLE "Order" DROP COLUMN "total_paid",
ALTER COLUMN "payment_id" SET NOT NULL;

-- AlterTable
ALTER TABLE "Referral" DROP COLUMN "reffered_id",
ADD COLUMN     "referred_id" INTEGER NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "User_tel_chat_id_key" ON "User"("tel_chat_id");

-- AddForeignKey
ALTER TABLE "Order" ADD CONSTRAINT "Order_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "Payment"("payment_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Referral" ADD CONSTRAINT "Referral_referred_id_fkey" FOREIGN KEY ("referred_id") REFERENCES "User"("user_id") ON DELETE RESTRICT ON UPDATE CASCADE;
