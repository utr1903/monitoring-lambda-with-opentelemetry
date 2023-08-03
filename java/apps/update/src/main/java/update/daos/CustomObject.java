package update.daos;

public class CustomObject {

  private String item;
  private boolean isUpdated;
  private boolean isChecked;

  public CustomObject(
      String item,
      boolean isUpdated,
      boolean isChecked) {
    this.item = item;
    this.isUpdated = isUpdated;
    this.isChecked = isChecked;
  }

  public String getItem() {
    return this.item;
  }

  public void setIsUpdated(boolean isUpdated) {
    this.isUpdated = isUpdated;
  }

  public boolean getIsUpdated() {
    return this.isUpdated;
  }

  public boolean getIsChecked() {
    return this.isChecked;
  }
}
