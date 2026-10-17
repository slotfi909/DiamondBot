-- AlterEnum
ALTER TYPE "Field" ADD VALUE 'HUMANITIES';

-- AlterTable
ALTER TABLE "Product" ADD COLUMN     "deleted_at" TIMESTAMP(3);
