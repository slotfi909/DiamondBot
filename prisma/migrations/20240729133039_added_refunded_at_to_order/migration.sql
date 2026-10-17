-- AlterEnum
ALTER TYPE "Grade" ADD VALUE 'DIPLOMA';

-- DropForeignKey
ALTER TABLE "Order" DROP CONSTRAINT "Order_payment_id_fkey";

-- AlterTable
ALTER TABLE "Order" ADD COLUMN     "refunded_at" TIMESTAMP(3),
ALTER COLUMN "payment_id" DROP NOT NULL;

-- AlterTable
ALTER TABLE "User" ALTER COLUMN "tel_chat_id" DROP DEFAULT;

-- AddForeignKey
ALTER TABLE "Order" ADD CONSTRAINT "Order_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "Payment"("payment_id") ON DELETE SET NULL ON UPDATE CASCADE;
