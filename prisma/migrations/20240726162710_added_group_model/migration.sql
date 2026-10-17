-- CreateTable
CREATE TABLE "Group" (
    "group_id" SERIAL NOT NULL,
    "tel_group_id" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Group_pkey" PRIMARY KEY ("group_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Group_tel_group_id_key" ON "Group"("tel_group_id");
