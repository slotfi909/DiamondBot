/*
  Warnings:

  - You are about to drop the column `order_id` on the `Referral` table. All the data in the column will be lost.

*/
-- DropForeignKey
ALTER TABLE "Referral" DROP CONSTRAINT "Referral_order_id_fkey";

-- DropIndex
DROP INDEX "Referral_order_id_key";

-- AlterTable
ALTER TABLE "Order" ADD COLUMN     "referralReferral_id" INTEGER;

-- AlterTable
ALTER TABLE "Referral" DROP COLUMN "order_id";

-- AddForeignKey
ALTER TABLE "Order" ADD CONSTRAINT "Order_referralReferral_id_fkey" FOREIGN KEY ("referralReferral_id") REFERENCES "Referral"("referral_id") ON DELETE SET NULL ON UPDATE CASCADE;
